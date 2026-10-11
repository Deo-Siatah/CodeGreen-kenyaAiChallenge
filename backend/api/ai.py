from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from repositories.scoring_repository import ScoringRepository
from repositories.verification_repository import VerificationRepository
from services.explainability.explainability_service import (
    ExplanationGenerationError,
    ExplainabilityService,
)
from services.explainability.gemini_provider import GeminiExplanationProvider
from services.scoring_service import ScoreComputationResult

router = APIRouter(prefix="/ai", tags=["AI Explainability"])

# Gemini is injected once at the API composition boundary. Unit callers can
# construct ExplainabilityService with a fake provider and never import Gemini.
explainability_service = ExplainabilityService(GeminiExplanationProvider())
scoring_repository = ScoringRepository()
verification_repository = VerificationRepository()


@router.post("/explain/{session_id}")
async def generate_explanation(
    session_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Explain the persisted score for a completed verification session."""
    verification_session = await verification_repository.get_session(session, session_id)
    if verification_session is None:
        raise HTTPException(status_code=404, detail="Verification session not found")
    if verification_session.status not in {"complete", "completed"}:
        raise HTTPException(status_code=400, detail="Verification session is not complete")

    profile = await scoring_repository.get_current_score(
        session, verification_session.farmer_id
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="No score exists for this farmer")
    components = await scoring_repository.get_score_components(session, profile.id)
    breakdown = ScoreComputationResult(
        profile=profile,
        components=list(components),
        axis_note=(
            "capacity axis unavailable - character only"
            if profile.capacity_score is None
            else "combined"
        ),
    )
    try:
        explanation = await explainability_service.explain(breakdown)
    except ExplanationGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"session_id": session_id, "explanation": explanation}
