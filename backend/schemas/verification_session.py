# schemas/verification_session.py

from pydantic import BaseModel


class StartVerificationRequest(BaseModel):
    farmer_id: str