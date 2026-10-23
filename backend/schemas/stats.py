from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CountyCount(BaseModel):
    county: str | None
    count: int


class FarmerStats(BaseModel):
    total: int
    scored: int
    unscored: int
    counties: list[CountyCount]


class ScoreBucket(BaseModel):
    label: str
    count: int


class DecisionStats(BaseModel):
    eligible: int
    review_required: int
    decline: int
    unscored: int


class ScoreStats(BaseModel):
    scored: int
    mean_final: float | None
    mean_character: float | None
    mean_capacity: float | None
    buckets: list[ScoreBucket]
    decisions: DecisionStats


class NetworkStats(BaseModel):
    trust_sources: int
    market_actors: int
    social_groups: int
    links: int
    sessions: int
    completed_sessions: int
    participants: int
    responded_participants: int
    response_rate: float | None


class RecentLoan(BaseModel):
    id: UUID
    farmer_id: UUID
    amount: float
    status: str
    applied_at: datetime


class LoanStats(BaseModel):
    total: int
    pending: int
    pending_disbursement: int
    disbursed: int
    repaid: int
    defaulted: int
    total_amount: float
    disbursed_amount: float
    repaid_amount: float
    defaulted_amount: float
    repayment_rate: float | None
    recent: list[RecentLoan]


class ComponentStats(BaseModel):
    component_name: str
    mean_contribution: float
    sample_size: int


class GenderScore(BaseModel):
    gender: str
    count: int
    mean_final: float | None


class ScatterPoint(BaseModel):
    acreage: float
    final_score: float


class FairnessStats(BaseModel):
    excluded_inputs: list[str]
    character_axis_weight: float
    capacity_axis_weight: float
    capacity_coverage: float | None
    gender: list[GenderScore]
    acreage_vs_score: list[ScatterPoint]
    acreage_score_correlation: float | None


class RecentCase(BaseModel):
    id: UUID
    full_name: str
    county: str | None
    final_score: float | None
    decision: str | None
    recommended_amount: float | None
    created_at: datetime
    loan_status: str | None


class StatsOverviewResponse(BaseModel):
    generated_at: datetime
    farmers: FarmerStats
    scores: ScoreStats
    network: NetworkStats
    loans: LoanStats
    components: list[ComponentStats]
    fairness: FairnessStats
    recent_cases: list[RecentCase]
