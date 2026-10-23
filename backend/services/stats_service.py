from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import sqrt
from uuid import UUID

from schemas.stats import (
    ComponentStats,
    CountyCount,
    DecisionStats,
    FairnessStats,
    FarmerStats,
    GenderScore,
    LoanStats,
    NetworkStats,
    RecentCase,
    RecentLoan,
    ScatterPoint,
    ScoreBucket,
    ScoreStats,
    StatsOverviewResponse,
)
from services import weighting

BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("0-19", 0.0, 20.0),
    ("20-39", 20.0, 40.0),
    ("40-59", 40.0, 60.0),
    ("60-74", 60.0, 75.0),
    ("75-100", 75.0, 100.0001),
)

EXCLUDED_INPUTS = [
    "gender",
    "ethnicity",
    "religion",
    "disability",
    "age",
    "raw acreage",
]


@dataclass(frozen=True)
class FarmerRow:
    id: UUID
    full_name: str
    county: str | None
    gender: str | None
    created_at: datetime


@dataclass(frozen=True)
class ScoreRow:
    farmer_id: UUID
    final_score: float
    character_score: float
    capacity_score: float | None
    decision: str | None
    recommended_amount: float | None


@dataclass(frozen=True)
class ComponentRow:
    component_name: str
    contribution: float | None


@dataclass(frozen=True)
class LoanRow:
    id: UUID
    farmer_id: UUID
    amount: float
    status: str
    applied_at: datetime


@dataclass(frozen=True)
class StatsSnapshot:
    farmers: Sequence[FarmerRow]
    scores: Sequence[ScoreRow]
    components: Sequence[ComponentRow]
    loans: Sequence[LoanRow]
    acreage_by_farmer: dict[UUID, float | None]
    trust_sources: int = 0
    market_actors: int = 0
    social_groups: int = 0
    links: int = 0
    sessions: int = 0
    completed_sessions: int = 0
    participants: int = 0
    responded_participants: int = 0
    extra: dict[str, int] = field(default_factory=dict)


def score_bucket_label(value: float) -> str:
    for label, lower, upper in BUCKETS:
        if lower <= value < upper:
            return label
    return BUCKETS[-1][0]


def pearson_correlation(points: Sequence[tuple[float, float]]) -> float | None:

    if len(points) < 2:
        return None
    mean_x = sum(x for x, _ in points) / len(points)
    mean_y = sum(y for _, y in points) / len(points)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in points)
    variance_x = sum((x - mean_x) ** 2 for x, _ in points)
    variance_y = sum((y - mean_y) ** 2 for _, y in points)
    if variance_x == 0 or variance_y == 0:
        return None
    return round(numerator / sqrt(variance_x * variance_y), 4)


def repayment_rate(repaid: int, defaulted: int) -> float | None:
    resolved = repaid + defaulted
    if resolved == 0:
        return None
    return round(repaid / resolved, 4)


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _county_counts(farmers: Sequence[FarmerRow]) -> list[CountyCount]:
    counts = Counter(farmer.county or "Unknown" for farmer in farmers)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
    return [CountyCount(county=county, count=count) for county, count in ordered]


def _component_stats(components: Sequence[ComponentRow]) -> list[ComponentStats]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for component in components:
        if component.contribution is not None:
            grouped[component.component_name].append(float(component.contribution))
    rows = [
        ComponentStats(
            component_name=name,
            mean_contribution=round(sum(values) / len(values), 2),
            sample_size=len(values),
        )
        for name, values in grouped.items()
    ]
    rows.sort(key=lambda item: (-item.sample_size, item.component_name))
    return rows


def _gender_stats(
    farmers: Sequence[FarmerRow], scores_by_farmer: dict[UUID, ScoreRow]
) -> list[GenderScore]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for farmer in farmers:
        grouped[farmer.gender or "unknown"].append(
            scores_by_farmer[farmer.id].final_score if farmer.id in scores_by_farmer else None
        )

    rows: list[GenderScore] = []
    for gender, values in sorted(grouped.items()):
        scored = [value for value in values if value is not None]
        rows.append(
            GenderScore(
                gender=gender,
                count=len(values),
                mean_final=_mean(scored),
            )
        )
    return rows


def _recent_loans(loans: Sequence[LoanRow], limit: int = 10) -> list[RecentLoan]:
    ordered = sorted(loans, key=lambda loan: loan.applied_at, reverse=True)[:limit]
    return [
        RecentLoan(
            id=loan.id,
            farmer_id=loan.farmer_id,
            amount=float(loan.amount),
            status=loan.status,
            applied_at=loan.applied_at,
        )
        for loan in ordered
    ]


def build_overview(
    snapshot: StatsSnapshot, *, now: datetime | None = None
) -> StatsOverviewResponse:
    generated_at = now or datetime.now(timezone.utc)
    total_farmers = len(snapshot.farmers)
    scores_by_farmer = {score.farmer_id: score for score in snapshot.scores}
    scored = len(snapshot.scores)
    unscored = max(0, total_farmers - scored)

    final_values = [float(score.final_score) for score in snapshot.scores]
    character_values = [float(score.character_score) for score in snapshot.scores]
    capacity_values = [
        float(score.capacity_score)
        for score in snapshot.scores
        if score.capacity_score is not None
    ]

    bucket_counts = Counter(score_bucket_label(value) for value in final_values)
    buckets = [
        ScoreBucket(label=label, count=bucket_counts.get(label, 0))
        for label, _, _ in BUCKETS
    ]

    decision_counts = Counter(score.decision for score in snapshot.scores)
    decisions = DecisionStats(
        eligible=decision_counts.get("ELIGIBLE", 0),
        review_required=decision_counts.get("REVIEW_REQUIRED", 0),
        decline=decision_counts.get("DECLINE", 0),
        unscored=unscored,
    )

    loan_counts = Counter(loan.status for loan in snapshot.loans)

    def loan_total(*statuses: str) -> float:
        return round(
            sum(float(loan.amount) for loan in snapshot.loans if loan.status in statuses),
            2,
        )

    total_amount = round(sum(float(loan.amount) for loan in snapshot.loans), 2)
    repaid = loan_counts.get("repaid", 0)
    defaulted = loan_counts.get("defaulted", 0)
    disbursed_amount = loan_total("disbursed", "repaid", "defaulted")

    acreage_points = [
        (float(acreage), float(score.final_score))
        for score in snapshot.scores
        if (acreage := snapshot.acreage_by_farmer.get(score.farmer_id)) is not None
    ]
    scatter = [
        ScatterPoint(acreage=acreage, final_score=final_score)
        for acreage, final_score in acreage_points
    ]

    latest_loan: dict[UUID, LoanRow] = {}
    for loan in snapshot.loans:
        current = latest_loan.get(loan.farmer_id)
        if current is None or loan.applied_at > current.applied_at:
            latest_loan[loan.farmer_id] = loan

    recent_cases = [
        RecentCase(
            id=farmer.id,
            full_name=farmer.full_name,
            county=farmer.county,
            final_score=(
                float(scores_by_farmer[farmer.id].final_score)
                if farmer.id in scores_by_farmer
                else None
            ),
            decision=(
                scores_by_farmer[farmer.id].decision
                if farmer.id in scores_by_farmer
                else None
            ),
            recommended_amount=(
                scores_by_farmer[farmer.id].recommended_amount
                if farmer.id in scores_by_farmer
                else None
            ),
            created_at=farmer.created_at,
            loan_status=(
                latest_loan[farmer.id].status if farmer.id in latest_loan else None
            ),
        )
        for farmer in sorted(
            snapshot.farmers, key=lambda farmer: farmer.created_at, reverse=True
        )[:12]
    ]

    return StatsOverviewResponse(
        generated_at=generated_at,
        farmers=FarmerStats(
            total=total_farmers,
            scored=scored,
            unscored=unscored,
            counties=_county_counts(snapshot.farmers),
        ),
        scores=ScoreStats(
            scored=scored,
            mean_final=_mean(final_values),
            mean_character=_mean(character_values),
            mean_capacity=_mean(capacity_values),
            buckets=buckets,
            decisions=decisions,
        ),
        network=NetworkStats(
            trust_sources=snapshot.trust_sources,
            market_actors=snapshot.market_actors,
            social_groups=snapshot.social_groups,
            links=snapshot.links,
            sessions=snapshot.sessions,
            completed_sessions=snapshot.completed_sessions,
            participants=snapshot.participants,
            responded_participants=snapshot.responded_participants,
            response_rate=repayment_rate(
                snapshot.responded_participants,
                snapshot.participants - snapshot.responded_participants,
            ),
        ),
        loans=LoanStats(
            total=len(snapshot.loans),
            pending=loan_counts.get("pending", 0),
            pending_disbursement=loan_counts.get("pending_disbursement", 0),
            disbursed=loan_counts.get("disbursed", 0),
            repaid=repaid,
            defaulted=defaulted,
            total_amount=total_amount,
            disbursed_amount=disbursed_amount,
            repaid_amount=loan_total("repaid"),
            defaulted_amount=loan_total("defaulted"),
            repayment_rate=repayment_rate(repaid, defaulted),
            recent=_recent_loans(snapshot.loans),
        ),
        components=_component_stats(snapshot.components),
        fairness=FairnessStats(
            excluded_inputs=EXCLUDED_INPUTS,
            character_axis_weight=weighting.CHARACTER_AXIS_WEIGHT,
            capacity_axis_weight=weighting.CAPACITY_AXIS_WEIGHT,
            capacity_coverage=(
                round(len(capacity_values) / scored, 4) if scored else None
            ),
            gender=_gender_stats(snapshot.farmers, scores_by_farmer),
            acreage_vs_score=scatter,
            acreage_score_correlation=pearson_correlation(acreage_points),
        ),
        recent_cases=recent_cases,
    )
