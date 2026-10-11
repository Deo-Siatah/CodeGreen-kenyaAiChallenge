from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class CurrentScore(BaseModel):
    final_score: Optional[float]
    decision: Optional[str]
    recommended_amount: Optional[float]


class FarmerResponse(BaseModel):
    id: UUID
    full_name: str
    county: Optional[str]
    created_at: str
    current_score: Optional[CurrentScore]


class FarmersListResponse(BaseModel):
    items: list[FarmerResponse]
    total: int