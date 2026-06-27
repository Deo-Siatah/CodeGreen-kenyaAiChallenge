from fastapi import APIRouter, HTTPException, Depends
from typing import Dict

from schemas.verification_request import (
    StartVerificationRequest,
    SendFinalSmsRequest,
    SimulateTimeoutRequest,
    StartVerificationResponse,
    VerificationStatusResponse,
    FinalResultResponse,
    SendSmsResponse,
    VerificationLogsResponse
)
from services.verification_service import VerificationService


from repositories.verification_session_repository import VerificationSessionRepository
from repositories.participant_response_repository import ParticipantResponseRepository
from repositories.verification_log_repository import VerificationLogRepository
from repositories.farmer_repository import FarmerRepository
from services.scoring_service import ScoringService
from services.sms_service import SmsService
from services.question_service import QuestionEngine
from services.verification_service import VerificationService


router = APIRouter(prefix="/api/verify", tags=["verification"])

from services.weighting_service import WeightingService
from services.scoring_service import ScoringService

def get_verification_service() -> VerificationService:
    session_repo = VerificationSessionRepository()
    response_repo = ParticipantResponseRepository()
    log_repo = VerificationLogRepository()
    farmer_repo = FarmerRepository()

    weighting_service = WeightingService()
    scoring_service = ScoringService(weighting_service)
    sms_service = SmsService()
    question_service = QuestionEngine()

    return VerificationService(
        session_repo=session_repo,
        response_repo=response_repo,
        log_repo=log_repo,
        farmer_repo=farmer_repo,
        scoring_service=scoring_service,
        sms_service=sms_service,
        question_service=question_service
    )


@router.post("/start", response_model=StartVerificationResponse)
def start_verification(
    payload: StartVerificationRequest,
    service: VerificationService = Depends(get_verification_service)
):
    """
    Start verification process for a farmer
    
    1. Creates VerificationSession
    2. Loads farmer's trust sources
    3. Creates ParticipantResponse records (pending)
    4. Returns session info with USSD codes
    """
    try:
        result = service.start_verification(payload.farmer_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/simulate-timeout", response_model=VerificationStatusResponse)
def simulate_timeout(
    session_id: str,
    payload: SimulateTimeoutRequest,
    service: VerificationService = Depends(get_verification_service)
):
    """
    Simulate timeout for a participant (demo only)
    Marks participant as non-responsive after 48h
    """
    try:
        result = service.simulate_timeout(session_id, payload.phone)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/status", response_model=VerificationStatusResponse)
def get_status(
    session_id: str,
    service: VerificationService = Depends(get_verification_service)
):
    """
    Get current verification status
    Shows: participants responded, pending, timeout, current score
    """
    try:
        result = service.get_status(session_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/result", response_model=FinalResultResponse)
def get_final_result(
    session_id: str,
    service: VerificationService = Depends(get_verification_service)
):
    """
    Get final verification result (only when complete)
    Returns: trust_score, decision, recommendation, analysis, participant_scores
    """
    try:
        result = service.get_final_result(session_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/send-sms", response_model=SendSmsResponse)
def send_final_sms(
    session_id: str,
    payload: SendFinalSmsRequest,
    service: VerificationService = Depends(get_verification_service)
):
    """
    Send final SMS to farmer with verification result
    Only works when session is complete or timeout
    """
    try:
        result = service.send_final_sms(session_id, payload.farmer_phone)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/logs", response_model=VerificationLogsResponse)
def get_logs(
    session_id: str,
    service: VerificationService = Depends(get_verification_service)
):
    """
    Get audit trail (sandbox visibility)
    Shows all events: started, participant contacted, response received, SMS sent, etc.
    """
    try:
        result = service.get_logs(session_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

