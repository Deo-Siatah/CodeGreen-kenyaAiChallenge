
from pydantic import BaseModel
from datetime import datetime

class RecommendationCreate(BaseModel):
    decision: str

    recommended_amount: float

    explanation: str

    strengths: list[str]

    risks: list[str]

    conditions: list[str]

    generated_at: datetime