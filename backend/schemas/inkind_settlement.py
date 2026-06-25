
from pydantic import BaseModel
from datetime import datetime

class InKindSettlementProofCreate(BaseModel):
    settlement_type: str

    estimated_value: float

    description: str

    verification_status: str

    counterparty_name: str | None = None

    date_recorded: datetime

    supporting_notes: str | None = None