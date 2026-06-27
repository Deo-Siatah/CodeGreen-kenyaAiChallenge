from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# ============ REQUEST SCHEMAS ============

class StartVerificationRequest(BaseModel):
    farmer_id: str = Field(..., description="UUID of the farmer")
    
    class Config:
        json_schema_extra = {
            "example": {
                "farmer_id": "farmer_001"
            }
        }


class USSDStartRequest(BaseModel):
    phone: str = Field(..., description="Phone number dialing USSD")
    session_id: str = Field(..., description="Verification session ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "0712345678",
                "session_id": "session_abc123"
            }
        }


class USSDResponseRequest(BaseModel):
    phone: str = Field(..., description="Phone number responding")
    session_id: str = Field(..., description="Verification session ID")
    answer: str = Field(..., description="YES, NO, or UNSURE")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "0712345678",
                "session_id": "session_abc123",
                "question_id": "Q1",
                "answer": "YES"
            }
        }


class SendFinalSmsRequest(BaseModel):
    farmer_phone: str = Field(..., description="Phone number to send SMS to")
    
    class Config:
        json_schema_extra = {
            "example": {
                "farmer_phone": "+254712345678"
            }
        }


class SimulateTimeoutRequest(BaseModel):
    phone: str = Field(..., description="Participant phone to mark as timeout")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+254712345678"
            }
        }


# ============ RESPONSE SCHEMAS ============

class ParticipantStatus(BaseModel):
    type: str
    name: str
    phone: str
    ussd_code: Optional[str] = None
    status: str  # pending, received, timeout


class StartVerificationResponse(BaseModel):
    session_id: str
    farmer_id: str
    status: str  # pending
    participants_awaiting: List[ParticipantStatus]
    message: str
    created_at: datetime


class ParticipantResponseStatus(BaseModel):
    phone: str
    status: str
    received_at: Optional[datetime] = None
    raw_score: Optional[float] = None
    weighted_score: Optional[float] = None


class VerificationStatusResponse(BaseModel):
    session_id: str
    status: str  # pending, complete, timeout
    participants: List[ParticipantResponseStatus]
    received: int
    pending: int
    current_score: Optional[float] = None
    message: str


class ParticipantScoreDetail(BaseModel):
    participant_type: str
    participant_name: str
    phone: str
    responses: List[dict]
    raw_score: float
    weight: float
    weighted_score: float


class AnalysisData(BaseModel):
    summary: str
    explanation: str
    key_drivers: List[str]
    risk_factors: List[str] = []


class FinalResultResponse(BaseModel):
    session_id: str
    farmer_id: str
    status: str  # complete
    created_at: datetime
    completed_at: datetime
    
    trust_score: float
    decision: str  # ELIGIBLE, REVIEW_REQUIRED, DECLINE
    recommendation: str  # APPROVE_LEVEL_1, APPROVE_LEVEL_2, DECLINE
    loan_amount_recommended_kes: Optional[float] = None
    
    participant_scores: List[ParticipantScoreDetail]
    analysis: AnalysisData


class SendSmsResponse(BaseModel):
    session_id: str
    status: str  # sms_sent
    farmer_phone: str
    message_sent: str
    sms_id: str
    sent_at: datetime
    message: str


class VerificationLogEvent(BaseModel):
    timestamp: datetime
    event: str
    participant: str | None = None
    phone: str | None = None
    details: dict


class VerificationLogsResponse(BaseModel):
    session_id: str
    created_at: datetime
    farmer_id: str
    events: List[VerificationLogEvent]

class AfricaTalkingUSSDRequest(BaseModel):
    phoneNumber: str
    sessionId: str
    serviceCode: str
    text: str
