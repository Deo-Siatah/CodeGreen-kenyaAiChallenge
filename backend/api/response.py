# api/responses.py

from fastapi import APIRouter

from schemas.verification_response import (
    VerificationResponseRequest
)

from services.response_service import (
    ResponseService
)

router = APIRouter(
    prefix="/responses",
    tags=["Responses"]
)

service = ResponseService()


@router.post(
    "/simulate/{session_id}"
)
def simulate_verification(
    session_id: str
):
    return service.simulate_verification(
        session_id
    )