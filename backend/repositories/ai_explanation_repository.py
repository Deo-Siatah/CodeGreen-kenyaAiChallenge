from datetime import datetime

from pydantic import BaseModel


class AIExplanationResponse(BaseModel):

    session_id: str

    trust_score: float

    decision: str

    recommendation: str

    loan_amount_recommended_kes: float | None = None

    loan_officer_explanation: str

    farmer_explanation: str

    swahili_translation: str

    creditworthiness_profile: str

    positive_signals: list[str]

    risk_signals: list[str]

    fairness_explanation: str

    created_at: datetime