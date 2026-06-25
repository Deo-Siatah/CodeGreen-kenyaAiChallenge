from pydantic import BaseModel
from datetime import date, datetime
class LoanCreate(BaseModel):
    amount: float

    purpose: str

    duration_months: int

    interest_rate: float | None = None

    status: str = "pending"

    application_date: datetime

    approval_date: datetime | None = None

    disbursement_date: datetime | None = None

    repayment_due_date: datetime | None = None