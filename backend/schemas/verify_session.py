from pydantic import BaseModel
from datetime import date, datetime
class VerificationSessionCreate(BaseModel):
    status: str

    created_at: datetime

    expires_at: datetime

    expected_responses: int

    received_responses: int = 0

    completion_percentage: float = 0.0