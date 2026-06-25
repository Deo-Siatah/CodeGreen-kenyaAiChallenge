from fastapi import APIRouter

from services.trust_service import TrustService

from schemas.trust_source import TrustSourceCreate
from schemas.institution import InstitutionCreate
from schemas.social_group import SocialGroupCreate
from schemas.market_actor import MarketActorCreate

router = APIRouter(
    prefix="/trust",
    tags=["Trust Network"]
)


@router.post("/sources")
def create_trust_source(
    payload: TrustSourceCreate
):
    return service.create_trust_source(
        payload.model_dump()
    )

@router.post("/institutions")
def create_institution(
    payload: InstitutionCreate
):
    return service.create_institution(
        payload.model_dump()
    )

@router.post("/social-groups")
def create_social_group(
    payload: SocialGroupCreate
):
    return service.create_social_group(
        payload.model_dump()
    )

@router.post("/market-actors")
def create_market_actor(
    payload: MarketActorCreate
):
    return service.create_market_actor(
        payload.model_dump()
    )

service = TrustService()