from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


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
    farmer: dict
    farms: List[Farm]
    trust_sources: List[TrustSource]
    market_actors: List[MarketActor]
    social_groups: List[SocialGroup]
    latest_session: Optional[LatestSession]
    current_score: Optional[CurrentScore]
    loans: List[Loan]