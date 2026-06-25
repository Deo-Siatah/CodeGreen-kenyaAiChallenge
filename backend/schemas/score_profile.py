
from pydantic import BaseModel


class FinancialSignalCreate(BaseModel):
    signal_type: str

    score: float

    period: str

    source: str

    confidence: float = 1.0

    evidence_reference: str | None = None