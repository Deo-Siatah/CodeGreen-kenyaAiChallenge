from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class FarmerRouteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str
    national_id: str
    phone: str
    gender: str
    date_of_birth: date | None = None
    location: str
    village: str | None = None
    sub_county: str | None = None
    county: str | None = None
    farming_type: str | None = None
    years_farming: int | None = None


class FarmRouteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acreage: float
    production_type: str | None = None
    latitude: float
    longitude: float


class LinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    related_id: str


class TrustSourceResponse(BaseModel):
    participant_type: Literal["trust_source"]
    rating: int | None = Field(ge=1, le=4, default=None)
    comments: str | None = None
    personal_knowledge_flag: bool = True


class MarketActorResponse(BaseModel):
    participant_type: Literal["market_actor"]
    reliability_rating: int = Field(ge=1, le=4)
    purchase_frequency: str | None = None
    relationship_months: int | None = None
    avg_volume_kg: float | None = None


class SocialGroupResponse(BaseModel):
    participant_type: Literal["social_group"]
    consecutive_cycles: int = Field(ge=0)
    last_contribution_date: date | None = None
    contribution_amount: float | None = None


VerificationResponsePayload = Annotated[
    TrustSourceResponse | MarketActorResponse | SocialGroupResponse,
    Field(discriminator="participant_type"),
]


class SettlementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    settlement_type: str
    estimated_value: float
    verification_status: str = "pending"
    counterparty_id: str | None = None


class VerificationStartRequest(BaseModel):
    farmer_id: str


class VerificationResultResponse(BaseModel):
    session_id: str
    score_profile: dict


class ExplanationResponse(BaseModel):
    session_id: str
    explanation: str
