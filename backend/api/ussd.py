from fastapi import APIRouter, HTTPException, Depends,Request,Form
from fastapi.responses import PlainTextResponse

from pydantic import BaseModel

from services.ussd_service import USSDService
from services.verification_service import VerificationService
from schemas.verification_request import USSDStartRequest, USSDResponseRequest,AfricaTalkingUSSDRequest
from utils.phone_normalization import normalize_phone

from repositories.verification_session_repository import VerificationSessionRepository
from repositories.participant_response_repository import ParticipantResponseRepository
from repositories.verification_log_repository import VerificationLogRepository
from repositories.farmer_repository import FarmerRepository

from services.scoring_service import ScoringService
from services.sms_service import SmsService
from services.question_service import QuestionEngine
from services.weighting_service import WeightingService


router = APIRouter(prefix="/api/ussd", tags=["ussd"])


# ------------------ Response Models ------------------

class USSDStartResponse(BaseModel):
    ussd_text: str
    session_state: str
    question_number: int
    total_questions: int


class USSDResponseSubmitResponse(BaseModel):
    ussd_text: str
    session_state: str
    question_number: int | None = None
    total_questions: int | None = None
    message: str | None = None


# ------------------ Dependency Factory ------------------

def get_ussd_service() -> USSDService:
    weighting_service = WeightingService()
    scoring_service = ScoringService(weighting_service)

    verification_service = VerificationService(
        session_repo=VerificationSessionRepository(),
        response_repo=ParticipantResponseRepository(),
        log_repo=VerificationLogRepository(),
        farmer_repo=FarmerRepository(),
        scoring_service=scoring_service,
        sms_service=SmsService(),
        question_service=QuestionEngine()
    )

    return USSDService(
        question_service=QuestionEngine(),
        verification_service=verification_service
    )


# ------------------ Routes ------------------

@router.post("/start", response_model=USSDStartResponse)
def start_ussd(
    payload: USSDStartRequest,
    service: USSDService = Depends(get_ussd_service)
):
    """Start USSD session when participant dials code."""
    try:
        return service.start_ussd(
            phone=payload.phone,
            session_id=payload.session_id,
            ussd_code=""  # Africa's Talking service code comes here
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/respond", response_model=USSDResponseSubmitResponse)
def submit_ussd_response(
    payload: USSDResponseRequest,
    service: USSDService = Depends(get_ussd_service)
):
    """Process USSD response (1, 2, or 3)."""
    try:
        return service.process_ussd_response(
            phone=payload.phone,
            session_id=payload.session_id,
            user_input=payload.answer
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/webhook/callback",
    response_class=PlainTextResponse
)
async def handle_ussd_callback(
    phoneNumber: str = Form(...),
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    text: str = Form(""),
    service: USSDService = Depends(get_ussd_service)
):
    phone = normalize_phone(phoneNumber)

    user_text = text.strip()

    # Africa's Talking sends cumulative input.
    # We only need the latest answer.
    if user_text:
        user_text = user_text.split("*")[-1].strip()

    if not user_text:

        result = service.start_ussd(
            phone=phone,
            session_id=sessionId,
            ussd_code=serviceCode
        )

    else:

        result = service.process_ussd_response(
            phone=phone,
            session_id=sessionId,
            user_input=user_text
        )


    # Africa's Talking expects plain text.

    if result["session_state"] == "question":
        return f"CON {result['ussd_text']}"

    return f"END {result['ussd_text']}"