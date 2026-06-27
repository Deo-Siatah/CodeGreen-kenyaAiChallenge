# api/verification.py

from fastapi import APIRouter

from schemas.verification_session import (
    StartVerificationRequest
)

from services.verification_orchestrator import (
    VerificationOrchestrator
)

router = APIRouter(
    prefix="/appverification",
    tags=["Verification"]
)

service = VerificationOrchestrator()


@router.post("/start")
def start_verification(
    payload: StartVerificationRequest
):

    return service.start_session(
        payload.farmer_id
    )