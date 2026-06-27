from fastapi import APIRouter, HTTPException

from services.explainability_service import ExplainabilityService
from services.verification_service import VerificationService

from repositories.verification_session_repository import (
    VerificationSessionRepository,
)
from repositories.participant_response_repository import (
    ParticipantResponseRepository,
)
from repositories.verification_log_repository import (
    VerificationLogRepository,
)
from repositories.farmer_repository import FarmerRepository

from services.weighting_service import WeightingService
from services.scoring_service import ScoringService
from services.sms_service import SmsService
from services.question_service import QuestionEngine


router = APIRouter(
    prefix="/ai",
    tags=["AI Explainability"]
)


# ---------------------------------------------------------
# Dependency Builders
# ---------------------------------------------------------

weighting_service = WeightingService()

scoring_service = ScoringService(
    weighting_service
)

verification_service = VerificationService(
    session_repo=VerificationSessionRepository(),
    response_repo=ParticipantResponseRepository(),
    log_repo=VerificationLogRepository(),
    farmer_repo=FarmerRepository(),
    scoring_service=scoring_service,
    sms_service=SmsService(),
    question_service=QuestionEngine()
)

explainability_service = ExplainabilityService()


# ---------------------------------------------------------
# Generate & Persist AI Explanation
# ---------------------------------------------------------

@router.post("/explain/{session_id}")
def generate_explanation(session_id: str):
    """
    Generate and save an AI explanation for a completed
    verification session.
    """

    verification_result = verification_service.get_final_result(
        session_id
    )

    if not verification_result:
        raise HTTPException(
            status_code=404,
            detail="Verification session not found."
        )

    if verification_result["status"] != "complete":
        raise HTTPException(
            status_code=400,
            detail="Verification session is not complete."
        )

    return explainability_service.generate_explanation(
        session_id=session_id,
        verification_result=verification_result
    )


# ---------------------------------------------------------
# Retrieve Stored AI Explanation
# ---------------------------------------------------------

@router.get("/explain/{session_id}")
def get_explanation(session_id: str):
    """
    Retrieve the stored AI explanation for a verification
    session.
    """

    explanation = explainability_service.get_explanation(
        session_id
    )

    if explanation is None:
        raise HTTPException(
            status_code=404,
            detail="AI explanation not found."
        )

    return explanation