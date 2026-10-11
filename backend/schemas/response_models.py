from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


# Farmers
class FarmerRouteCreate(BaseModel):
    full_name: str
    national_id: str
    phone: str
    gender: str
    date_of_birth: Optional[str] = None
    location: str
    village: Optional[str] = None
    sub_county: Optional[str] = None
    county: Optional[str] = None
    farming_type: Optional[str] = None
    years_farming: Optional[int] = None


class FarmerResponse(BaseModel):
    id: UUID
    full_name: str
    national_id: str
    phone: str
    gender: str
    date_of_birth: Optional[str] = None
    location: str
    village: Optional[str] = None
    sub_county: Optional[str] = None
    county: Optional[str] = None
    farming_type: Optional[str] = None
    years_farming: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class FarmersListResponse(BaseModel):
    items: List[FarmerResponse]
    total: int


# Farms
class FarmRouteCreate(BaseModel):
    acreage: float
    production_type: Optional[str] = None
    latitude: float
    longitude: float


class FarmResponse(BaseModel):
    id: UUID
    farmer_id: UUID
    acreage: Optional[float]
    production_type: Optional[str] = None
    latitude: Optional[float]
    longitude: Optional[float]
    created_at: datetime
    updated_at: datetime


# Trust Sources
class TrustSourceCreate(BaseModel):
    name: str
    category: str
    phone: Optional[str] = None
    national_id: Optional[str] = None
    location: str


class TrustSourceResponse(BaseModel):
    id: UUID
    full_name: str
    category: str
    phone: Optional[str] = None
    national_id: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Institutions
class InstitutionCreate(BaseModel):
    name: str
    type: Optional[str] = None
    registration_number: Optional[str] = None
    county: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class InstitutionResponse(BaseModel):
    id: UUID
    name: str
    type: Optional[str] = None
    registration_number: Optional[str] = None
    county: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Social Groups
class SocialGroupCreate(BaseModel):
    name: str
    group_type: Optional[str] = None
    location: Optional[str] = None
    formation_year: Optional[int] = None


class SocialGroupResponse(BaseModel):
    id: UUID
    name: str
    group_type: Optional[str] = None
    location: Optional[str] = None
    formation_year: Optional[int] = None
    created_at: datetime
    updated_at: datetime


# Market Actors
class MarketActorCreate(BaseModel):
    name: str
    actor_type: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None


class MarketActorResponse(BaseModel):
    id: UUID
    name: str
    actor_type: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Verification
class LinkRequest(BaseModel):
    related_id: str


class TrustSourceResponse(BaseModel):
    participant_type: str = "trust_source"
    rating: Optional[int] = None
    comments: Optional[str] = None
    personal_knowledge_flag: bool = True


class MarketActorResponse(BaseModel):
    participant_type: str = "market_actor"
    reliability_rating: int
    purchase_frequency: Optional[str] = None
    relationship_months: Optional[int] = None
    avg_volume_kg: Optional[float] = None


class SocialGroupResponse(BaseModel):
    participant_type: str = "social_group"
    consecutive_cycles: int
    last_contribution_date: Optional[str] = None
    contribution_amount: Optional[float] = None


VerificationResponsePayload = TrustSourceResponse | MarketActorResponse | SocialGroupResponse


class VerificationStartRequest(BaseModel):
    farmer_id: str


class VerificationResultResponse(BaseModel):
    session_id: str
    score_profile: Dict[str, Any]


class ExplanationResponse(BaseModel):
    session_id: str
    explanation: str


class SettlementRequest(BaseModel):
    settlement_type: str
    estimated_value: float
    verification_status: str = "pending"
    counterparty_id: Optional[str] = None


# Loans
class LoanCreate(BaseModel):
    farmer_id: str
    amount: float
    purpose: str
    duration_months: int
    interest_rate: float


class LoanResponse(BaseModel):
    id: UUID
    farmer_id: UUID
    amount: float
    purpose: str
    duration_months: int
    interest_rate: float
    status: str
    created_at: datetime
    updated_at: datetime


class LoansListResponse(BaseModel):
    items: List[LoanResponse]
    total: int


# Network
class Farm(BaseModel):
    id: UUID
    acreage: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]


class TrustSource(BaseModel):
    id: UUID
    name: str
    category: str
    phone_masked: Optional[str]
    credibility_score: float


class MarketActor(BaseModel):
    id: UUID
    name: str
    actor_type: str
    phone_masked: Optional[str]
    credibility_score: float


class SocialGroup(BaseModel):
    id: UUID
    name: str
    group_type: str


class Participant(BaseModel):
    id: UUID
    participant_type: str
    participant_id: UUID
    responded: Optional[datetime]


class LatestSession(BaseModel):
    id: UUID
    status: str
    participants: List[Participant]


class CurrentScore(BaseModel):
    id: UUID
    character_score: Optional[float]
    capacity_score: Optional[float]
    final_score: Optional[float]
    decision: Optional[str]
    recommended_amount: Optional[float]


class Loan(BaseModel):
    id: UUID
    amount: Optional[float]
    status: str
    applied_at: Optional[datetime]


class NetworkResponse(BaseModel):
    farmer: Dict[str, Any]
    farms: List[Farm]
    trust_sources: List[TrustSource]
    market_actors: List[MarketActor]
    social_groups: List[SocialGroup]
    latest_session: Optional[LatestSession]
    current_score: Optional[CurrentScore]
    loans: List[Loan]


# Breakdown
class BreakdownComponent(BaseModel):
    axis: str
    component_name: str
    raw_value: str
    contribution: Optional[float]
    weight: Optional[float]
    pool_id: Optional[UUID]
    trust_source_id: Optional[UUID]
    market_actor_id: Optional[UUID]


class BreakdownResponse(BaseModel):
    profile: Dict[str, Any]
    axis_note: str
    components: List[BreakdownComponent]