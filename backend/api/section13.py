from __future__ import annotations

import logging
from typing import Literal 
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db_session
from repositories.scoring_repository import ScoringRepository
from repositories.verification_repository import VerificationRepository
from schemas.section13 import (
    ExplanationResponse,
    FarmRouteCreate,
    FarmerRouteCreate,
    LinkRequest,
    SettlementRequest,
    VerificationResponsePayload,
    VerificationResultResponse,
    VerificationStartRequest,
)
from schemas.farmers import FarmersListResponse
from schemas.network import NetworkResponse
from schemas.breakdown import BreakdownResponse
from schemas.institution import InstitutionCreate
from schemas.loan import LoanCreate
from services.loan_service import (
    NoScoreError,
    LoanNotEligibleError,
    AmountExceedsRecommendationError,
    OpenLoanExistsError,
    LoanNotFoundError,
    InvalidLoanStateError,
    LoanService,
)
from services.farmer_service import DuplicateFarmerError
from schemas.market_actor import MarketActorCreate
from schemas.social_group import SocialGroupCreate
from schemas.trust_source import TrustSourceCreate
from services.explainability.explainability_service import (
    ExplanationGenerationError,
    ExplainabilityService,
)
from services.farmer_service import FarmerService
from services.scoring_service import ScoreComputationResult
from services.trust_service import TrustService
from services.verification_service import (
    ParticipantAlreadyRespondedError,
    ParticipantNotFoundError,
    VerificationService,
)

router = APIRouter(prefix="/api", tags=["Section 13"])
logger = logging.getLogger(__name__)


def get_farmer_service() -> FarmerService:
    from main import get_farmer_service as factory

    return factory()


def get_trust_service() -> TrustService:
    from main import get_trust_service as factory

    return factory()


def get_verification_service() -> VerificationService:
    from main import get_verification_service as factory

    return factory()


def get_explainability_service() -> ExplainabilityService:
    from main import get_explainability_service as factory

    return factory()


def _columns(obj) -> dict:
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


@router.post("/farmers", response_model=dict)
async def create_farmer(
    payload: FarmerRouteCreate,
    session: AsyncSession = Depends(get_db_session),
    service: FarmerService = Depends(get_farmer_service),
):
    try:
        result = await service.create_farmer(session, payload.model_dump())
        await session.commit()
        return _columns(result)
    except DuplicateFarmerError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/farmers/{farmer_id}/farm", response_model=dict)
async def create_farm(
    farmer_id: UUID,
    payload: FarmRouteCreate,
    session: AsyncSession = Depends(get_db_session),
    service: FarmerService = Depends(get_farmer_service),
):
    result = await service.create_farm(session, farmer_id, payload.model_dump())
    await session.commit()
    return _columns(result)


@router.get("/farmers/{farmer_id}", response_model=dict)
async def get_farmer(
    farmer_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: FarmerService = Depends(get_farmer_service),
):
    result = await service.get_farmer(session, farmer_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return _columns(result)


async def _create_trust(payload, service_method, session, service):
    result = await service_method(session, payload.model_dump())
    await session.commit()
    return _columns(result)


@router.post("/trust/sources", response_model=dict)
async def create_trust_source(
    payload: TrustSourceCreate,
    session=Depends(get_db_session),
    service=Depends(get_trust_service),
):
    return await _create_trust(payload, service.create_trust_source, session, service)


@router.post("/trust/institutions", response_model=dict)
async def create_institution(
    payload: InstitutionCreate,
    session=Depends(get_db_session),
    service=Depends(get_trust_service),
):
    return await _create_trust(payload, service.create_institution, session, service)


@router.post("/trust/social-groups", response_model=dict)
async def create_social_group(
    payload: SocialGroupCreate,
    session=Depends(get_db_session),
    service=Depends(get_trust_service),
):
    return await _create_trust(payload, service.create_social_group, session, service)


@router.post("/trust/market-actors", response_model=dict)
async def create_market_actor(
    payload: MarketActorCreate,
    session=Depends(get_db_session),
    service=Depends(get_trust_service),
):
    return await _create_trust(payload, service.create_market_actor, session, service)


async def _link(service_method, farmer_id, payload, session):
    result = await service_method(session, farmer_id, payload.related_id)
    await session.commit()
    return _columns(result)


@router.post("/farmers/{farmer_id}/link-trust-source", response_model=dict)
async def link_trust_source(
    farmer_id: UUID,
    payload: LinkRequest,
    session=Depends(get_db_session),
    service=Depends(get_trust_service),
):
    return await _link(service.link_trust_source, farmer_id, payload, session)


@router.post("/farmers/{farmer_id}/link-institution", response_model=dict)
async def link_institution(
    farmer_id: UUID,
    payload: LinkRequest,
    session=Depends(get_db_session),
    service=Depends(get_trust_service),
):
    return await _link(service.link_institution, farmer_id, payload, session)


@router.post("/farmers/{farmer_id}/link-social-group", response_model=dict)
async def link_social_group(
    farmer_id: UUID,
    payload: LinkRequest,
    session=Depends(get_db_session),
    service=Depends(get_trust_service),
):
    return await _link(service.link_social_group, farmer_id, payload, session)


@router.post("/farmers/{farmer_id}/link-market-actor", response_model=dict)
async def link_market_actor(
    farmer_id: UUID,
    payload: LinkRequest,
    session=Depends(get_db_session),
    service=Depends(get_trust_service),
):
    return await _link(service.link_market_actor, farmer_id, payload, session)


@router.post("/verify/start", response_model=dict)
async def start_verification(
    payload: VerificationStartRequest,
    session=Depends(get_db_session),
    service=Depends(get_verification_service),
):
    result = await service.start_verification(session, payload.farmer_id)
    await session.commit()
    return {
        "session_id": str(result.id),
        "farmer_id": str(result.farmer_id),
        "status": result.status,
    }


@router.post("/verify/{session_id}/respond/{participant_id}", response_model=dict)
async def submit_response(
    session_id: UUID,
    participant_id: UUID,
    payload: VerificationResponsePayload,
    session=Depends(get_db_session),
    service=Depends(get_verification_service),
):
    try:
        result = await service.submit_response(
            session, session_id, participant_id, payload.model_dump()
        )
    except ParticipantAlreadyRespondedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ParticipantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "Verification response failed: session_id=%s participant_id=%s",
            session_id,
            participant_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Verification response failed: {type(exc).__name__}: {exc}",
        ) from exc
    await session.commit()
    return result


@router.post("/verify/{session_id}/timeout/{participant_id}", response_model=dict)
async def timeout_participant(
    session_id: UUID,
    participant_id: UUID,
    session=Depends(get_db_session),
    service=Depends(get_verification_service),
):
    try:
        result = await service.mark_participant_timeout(session, session_id, participant_id)
    except ParticipantAlreadyRespondedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ParticipantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return result


@router.get("/verify/{session_id}/status", response_model=dict)
async def verification_status(
    session_id: UUID,
    session=Depends(get_db_session),
    service=Depends(get_verification_service),
):
    verification_session, participants = await service.get_session_with_participants(
        session, session_id
    )
    if verification_session is None:
        raise HTTPException(status_code=404, detail="Verification session not found")
    return {
        "session_id": str(session_id),
        "status": verification_session.status,
        "participants": [_columns(item) for item in participants],
    }


@router.get("/verify/{session_id}/result", response_model=VerificationResultResponse)
async def verification_result(session_id: UUID, session=Depends(get_db_session)):
    verification_session = await VerificationRepository().get_session(session, session_id)
    if verification_session is None:
        raise HTTPException(status_code=404, detail="Verification session not found")
    profile = await ScoringRepository().get_current_score(
        session, verification_session.farmer_id
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Score not found")
    return {"session_id": str(session_id), "score_profile": _columns(profile)}


@router.get("/verify/{session_id}/explanation", response_model=ExplanationResponse)
async def verification_explanation(
    session_id: UUID,
    session=Depends(get_db_session),
    service=Depends(get_explainability_service),
    mode: Literal["expert", "farmer"] | None = Query(default=None),
    language: str = Query(default=None, pattern=r"^[A-Za-z][A-Za-z \\-]{1,29}$"),
):
    # This route uses get_db_session, not get_scoring_session: it only reads
    # Validate mode parameter
    if mode is not None and mode not in ['expert', 'farmer']:
        raise HTTPException(
            status_code=422,
            detail='Invalid mode. Must be expert or farmer'
        )

    # verification_sessions, score_profiles, and score_components - never
    # the farmers table - so the restricted scoring role has no gender-
    # exposure risk here to guard against. get_scoring_session is reserved
    # for a future call site that genuinely needs farmer-table context.
    try:
        verification_session = await VerificationRepository().get_session(
            session, session_id
        )
        if verification_session is None:
            raise HTTPException(
                status_code=404, detail="Verification session not found"
            )

        logger.info(
            "Explanation lookup: session_id=%s farmer_id=%s",
            session_id,
            verification_session.farmer_id,
        )
        scoring_repository = ScoringRepository()
        profile = await scoring_repository.get_current_score(
            session, verification_session.farmer_id
        )
        if profile is None:
            raise HTTPException(status_code=404, detail="Score not found")
        components = await scoring_repository.get_score_components(session, profile.id)
        breakdown = ScoreComputationResult(
            profile,
            list(components),
            "combined"
            if profile.capacity_score is not None
            else "capacity axis unavailable - character only",
        )
        resolved_mode = mode or settings.DEFAULT_EXPLANATION_MODE
        explanation = await service.explain(breakdown, resolved_mode, language or "English")
        return {"session_id": str(session_id), "explanation": explanation}
    except HTTPException:
        raise
    except ExplanationGenerationError as exc:
        logger.exception(
            "Explanation provider failed: session_id=%s error_type=%s",
            session_id,
            type(exc.__cause__ or exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Explanation provider failed: {type(exc.__cause__ or exc).__name__}: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Explanation lookup or generation failed: session_id=%s error_type=%s",
            session_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Explanation request failed: {type(exc).__name__}: {exc}",
        ) from exc


@router.post("/farmers/{farmer_id}/inkind-settlement", response_model=dict)
async def create_settlement(
    farmer_id: UUID,
    payload: SettlementRequest,
    session: AsyncSession = Depends(get_db_session),
    service=Depends(get_verification_service),
):
    result = await service.create_settlement(session, farmer_id, payload.model_dump())
    await session.commit()
    return _columns(result)


def get_loan_service():
    from main import get_loan_service as factory

    return factory()


@router.post("/loans", response_model=dict)
async def create_loan(
    payload: LoanCreate,
    session: AsyncSession = Depends(get_db_session),
    service: LoanService = Depends(get_loan_service),
):
    """Create a new loan for a farmer."""
    try:
        result = await service.create_loan(
            session,
            payload.farmer_id,
            payload.amount,
            payload.purpose,
            payload.duration_months,
            payload.interest_rate,
        )
        await session.commit()
        return _columns(result)
    except NoScoreError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except LoanNotEligibleError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except AmountExceedsRecommendationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except OpenLoanExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except LoanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidLoanStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/loans/{loan_id}/disburse", response_model=dict)
async def mark_disbursed(
    loan_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: "LoanService" = Depends(get_loan_service),
):
    """Mark a loan as disbursed."""
    try:
        result = await service.mark_disbursed(session, loan_id)
        await session.commit()
        return _columns(result)
    except LoanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidLoanStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/loans/{loan_id}/repay", response_model=dict)
async def repay_loan(
    loan_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: "LoanService" = Depends(get_loan_service),
):
    """Repay a loan."""
    try:
        result = await service.resolve_loan(session, loan_id, "repaid")
        await session.commit()
        return _columns(result)
    except LoanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidLoanStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/loans/{loan_id}/default", response_model=dict)
async def default_loan(
    loan_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: "LoanService" = Depends(get_loan_service),
):
    """Mark a loan as defaulted."""
    try:
        result = await service.resolve_loan(session, loan_id, "defaulted")
        await session.commit()
        return _columns(result)
    except LoanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidLoanStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/loans", response_model=list)
async def get_loans(
    farmer_id: UUID | None = None,
    status: str | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Get loans, optionally filtered by farmer_id and/or status."""
    from repositories.loan_repository import LoanRepository
    
    repo = LoanRepository()
    loans = await repo.get_loans(session, farmer_id, status)
    return [_columns(loan) for loan in loans]


@router.get("/farmers", response_model=FarmersListResponse)
async def get_farmers(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
):
    """Get a paginated list of farmers with minimal data."""
    from repositories.farmer_repository import FarmerRepository
    
    repo = FarmerRepository()
    farmers, total = await repo.get_farmers_paginated(session, limit, offset)
    return {
        "items": [
            {
                "id": str(farmer.id),
                "full_name": farmer.full_name,
                "county": farmer.county,
                "created_at": farmer.created_at.isoformat(),
                "current_score": (
                    {
                        "final_score": profile.final_score,
                        "decision": profile.decision,
                        "recommended_amount": profile.recommended_amount,
                    }
                    if profile else None
                )
            }
            for farmer, profile in farmers
        ],
        "total": total,
    }


@router.get("/farmers/{farmer_id}/network", response_model=NetworkResponse)
async def get_farmer_network(
    farmer_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Get everything needed to redraw the graph for a farmer."""
    from repositories.farmer_repository import FarmerRepository
    from repositories.trust_repository import TrustRepository
    from repositories.verification_repository import VerificationRepository
    from repositories.scoring_repository import ScoringRepository
    from repositories.loan_repository import LoanRepository
    
    # Check if farmer exists
    farmer_repo = FarmerRepository()
    farmer = await farmer_repo.get_farmer(session, farmer_id)
    if farmer is None:
        raise HTTPException(status_code=404, detail="Farmer not found")
    
    # Get all related data
    trust_repo = TrustRepository()
    verification_repo = VerificationRepository()
    scoring_repo = ScoringRepository()
    loan_repo = LoanRepository()
    
    farms = await farmer_repo.get_farms(session, farmer_id)
    trust_sources = await trust_repo.get_farmer_trust_sources(session, farmer_id)
    market_actors = await trust_repo.get_market_actors_for_farmer(session, farmer_id)
    social_groups = await trust_repo.get_social_groups_for_farmer(session, farmer_id)
    latest_session = await verification_repo.get_latest_session(session, farmer_id)
    session_participants = (
        await verification_repo.list_participants_for_session(session, latest_session.id)
        if latest_session is not None
        else []
    )
    current_score = await scoring_repo.get_current_score(session, farmer_id)
    loans = await loan_repo.get_farmer_loans(session, farmer_id)
    
    # Mask phone numbers
    def mask_phone(phone):
        if not phone:
            return None
        if len(phone) >= 8:
            return f"{phone[:4]}*****{phone[-3:]}"
        return phone
    
    # Get credibility scores without creating rows
    credibility_scores = {}
    for trust_source in trust_sources:
        credibility_scores[str(trust_source.id)] = 1.0  # Default to 1.0 when no history
    
    for market_actor in market_actors:
        credibility_scores[str(market_actor.id)] = 1.0  # Default to 1.0 when no history
    
    return {
        "farmer": {
            "id": str(farmer.id),
            "full_name": farmer.full_name,
            "county": farmer.county,
        },
        "farms": [
            {
                "id": str(farm.id),
                "acreage": farm.acreage,
                "latitude": farm.latitude,
                "longitude": farm.longitude,
            }
            for farm in farms
        ],
        "trust_sources": [
            {
                "id": str(ts.id),
                "name": ts.full_name,
                "category": ts.category,
                "phone_masked": mask_phone(ts.phone),
                "credibility_score": credibility_scores.get(str(ts.id), 1.0),
            }
            for ts in trust_sources
        ],
        "market_actors": [
            {
                "id": str(ma.id),
                "name": ma.name,
                "actor_type": ma.actor_type,
                "phone_masked": mask_phone(ma.phone),
                "credibility_score": credibility_scores.get(str(ma.id), 1.0),
            }
            for ma in market_actors
        ],
        "social_groups": [
            {
                "id": str(sg.id),
                "name": sg.name,
                "group_type": sg.group_type,
            }
            for sg in social_groups
        ],
        "latest_session": (
            {
                "id": str(latest_session.id),
                "status": latest_session.status,
                "participants": [
                    {
                        "id": str(p.id),
                        "participant_type": p.participant_type,
                        "participant_id": p.participant_id,
                        "responded": p.responded_at.isoformat() if p.responded_at else None,
                    }
                    for p in session_participants
                ]
            }
            if latest_session else None
        ),
        "current_score": (
            {
                "id": str(current_score.id),
                "character_score": current_score.character_score,
                "capacity_score": current_score.capacity_score,
                "final_score": current_score.final_score,
                "decision": current_score.decision,
                "recommended_amount": current_score.recommended_amount,
            }
            if current_score else None
        ),
        "loans": [
            {
                "id": str(loan.id),
                "amount": loan.amount,
                "status": loan.status,
                "applied_at": loan.applied_at.isoformat(),
            }
            for loan in loans
        ],
    }


@router.get("/verify/{session_id}/breakdown", response_model=BreakdownResponse)
async def get_verification_breakdown(
    session_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Get score breakdown for a verification session."""
    from repositories.verification_repository import VerificationRepository
    from repositories.scoring_repository import ScoringRepository
    
    verification_repo = VerificationRepository()
    scoring_repo = ScoringRepository()
    
    verification_session = await verification_repo.get_session(session, session_id)
    if verification_session is None:
        raise HTTPException(status_code=404, detail="Verification session not found")
    
    profile = await scoring_repo.get_current_score(session, verification_session.farmer_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Score not found")
    
    components = await scoring_repo.get_score_components(session, profile.id)
    
    return {
        "profile": _columns(profile),
        "axis_note": "combined" if profile.capacity_score is not None else "capacity axis unavailable - character only",
        "components": [
            {
                "axis": component.axis,
                "component_name": component.component_name,
                "raw_value": component.raw_value,
                "contribution": component.contribution,
                "weight": component.weight,
                "pool_id": str(component.pool_id) if component.pool_id else None,
                "trust_source_id": str(component.trust_source_id) if component.trust_source_id else None,
                "market_actor_id": str(component.market_actor_id) if component.market_actor_id else None,
            }
            for component in components
        ],
    }


