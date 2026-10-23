from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from services.stats_service import (
    ComponentRow,
    FarmerRow,
    LoanRow,
    ScoreRow,
    StatsSnapshot,
    build_overview,
    pearson_correlation,
    repayment_rate,
    score_bucket_label,
)

BASE = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)

F1 = UUID("11111111-1111-4111-8111-111111111111")
F2 = UUID("22222222-2222-4222-8222-222222222222")
F3 = UUID("33333333-3333-4333-8333-333333333333")


def _farmers() -> list[FarmerRow]:
    return [
        FarmerRow(F1, "Grace Wambui", "Nakuru", "female", BASE + timedelta(days=3)),
        FarmerRow(F2, "Peter Otieno", "Kisumu", "male", BASE + timedelta(days=2)),
        FarmerRow(F3, "Amina Hassan", "Meru", "female", BASE + timedelta(days=1)),
    ]


def _scores() -> list[ScoreRow]:
    return [
        ScoreRow(F1, 80.0, 85.0, 75.0, "ELIGIBLE", 5000.0),
        ScoreRow(F2, 55.0, 55.0, None, "REVIEW_REQUIRED", None),
    ]


def _loans() -> list[LoanRow]:
    return [
        LoanRow(
            UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            F1,
            5000.0,
            "repaid",
            BASE + timedelta(days=4),
        ),
        LoanRow(
            UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            F2,
            3000.0,
            "defaulted",
            BASE + timedelta(days=5),
        ),
    ]


def _snapshot(**overrides) -> StatsSnapshot:
    values = {
        "farmers": _farmers(),
        "scores": _scores(),
        "components": [
            ComponentRow("testimony_pool", 82.0),
            ComponentRow("testimony_pool", 58.0),
            ComponentRow("cultivation_continuity", 75.0),
        ],
        "loans": _loans(),
        "acreage_by_farmer": {F1: 1.0, F2: 4.0, F3: None},
        "trust_sources": 4,
        "market_actors": 2,
        "social_groups": 1,
        "links": 9,
        "sessions": 3,
        "completed_sessions": 2,
        "participants": 8,
        "responded_participants": 6,
    }
    values.update(overrides)
    return StatsSnapshot(**values)


def test_score_bucket_edges_include_both_sides():
    assert score_bucket_label(0.0) == "0-19"
    assert score_bucket_label(19.99) == "0-19"
    assert score_bucket_label(20.0) == "20-39"
    assert score_bucket_label(59.99) == "40-59"
    assert score_bucket_label(60.0) == "60-74"
    assert score_bucket_label(74.99) == "60-74"
    assert score_bucket_label(75.0) == "75-100"
    assert score_bucket_label(100.0) == "75-100"


def test_pearson_correlation_handles_perfect_and_undefined_series():
    assert pearson_correlation([(1.0, 80.0), (4.0, 55.0)]) == -1.0
    assert pearson_correlation([(1.0, 50.0), (2.0, 60.0), (3.0, 70.0)]) == 1.0
    assert pearson_correlation([(1.0, 50.0)]) is None
    assert pearson_correlation([(1.0, 50.0), (1.0, 60.0)]) is None


def test_repayment_rate_is_none_until_a_loan_is_resolved():
    assert repayment_rate(0, 0) is None
    assert repayment_rate(3, 1) == 0.75
    assert repayment_rate(0, 2) == 0.0


def test_build_overview_aggregates_farmers_scores_loans_and_fairness():
    overview = build_overview(_snapshot(), now=BASE + timedelta(days=10))

    assert overview.farmers.total == 3
    assert overview.farmers.scored == 2
    assert overview.farmers.unscored == 1
    assert overview.farmers.counties[0].county == "Kisumu"
    assert overview.farmers.counties[0].count == 1

    assert overview.scores.mean_final == 67.5
    assert overview.scores.mean_character == 70.0
    assert overview.scores.mean_capacity == 75.0
    assert overview.scores.decisions.eligible == 1
    assert overview.scores.decisions.review_required == 1
    assert overview.scores.decisions.decline == 0
    assert overview.scores.decisions.unscored == 1

    buckets = {bucket.label: bucket.count for bucket in overview.scores.buckets}
    assert buckets == {"0-19": 0, "20-39": 0, "40-59": 1, "60-74": 0, "75-100": 1}

    assert overview.network.response_rate == 0.75
    assert overview.network.completed_sessions == 2

    assert overview.loans.total == 2
    assert overview.loans.repaid == 1
    assert overview.loans.defaulted == 1
    assert overview.loans.total_amount == 8000.0
    assert overview.loans.repaid_amount == 5000.0
    assert overview.loans.defaulted_amount == 3000.0
    assert overview.loans.repayment_rate == 0.5

    assert overview.fairness.capacity_coverage == 0.5
    assert overview.fairness.acreage_score_correlation == -1.0
    assert overview.fairness.character_axis_weight == 0.6
    assert overview.fairness.capacity_axis_weight == 0.4

    female = next(item for item in overview.fairness.gender if item.gender == "female")
    assert female.count == 2
    assert female.mean_final == 80.0

    testimony = next(
        item for item in overview.components if item.component_name == "testimony_pool"
    )
    assert testimony.sample_size == 2
    assert testimony.mean_contribution == 70.0

    assert [case.full_name for case in overview.recent_cases] == [
        "Grace Wambui",
        "Peter Otieno",
        "Amina Hassan",
    ]
    assert overview.recent_cases[0].loan_status == "repaid"
    assert overview.generated_at == BASE + timedelta(days=10)


def test_build_overview_is_safe_on_an_empty_database():
    overview = build_overview(
        StatsSnapshot(
            farmers=[],
            scores=[],
            components=[],
            loans=[],
            acreage_by_farmer={},
            trust_sources=0,
            market_actors=0,
            social_groups=0,
            links=0,
            sessions=0,
            completed_sessions=0,
            participants=0,
            responded_participants=0,
        ),
        now=BASE,
    )

    assert overview.farmers.total == 0
    assert overview.scores.mean_final is None
    assert [bucket.count for bucket in overview.scores.buckets] == [0, 0, 0, 0, 0]
    assert overview.network.response_rate is None
    assert overview.loans.repayment_rate is None
    assert overview.fairness.acreage_score_correlation is None
    assert overview.fairness.gender == []
    assert overview.recent_cases == []

