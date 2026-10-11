from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID


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
    profile: dict
    axis_note: str
    components: List[BreakdownComponent]