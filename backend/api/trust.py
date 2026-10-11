from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from services.trust_service import TrustService

from schemas.trust_source import TrustSourceCreate
from schemas.institution import InstitutionCreate
from schemas.social_group import SocialGroupCreate
from schemas.market_actor import MarketActorCreate

router = APIRouter(
    prefix="/trust",
    tags=["Trust Network"]
)


def _columns(obj) -> dict:
    """Flatten a freshly created row for the response.

    The service returns the ORM object so it stays usable as a service; handing
    that straight to FastAPI would fall back to vars() and drag the SQLAlchemy
    InstanceState into the response body.
    """
    return {
        column.name: getattr(obj, column.name)
        for column in obj.__table__.columns
    }


@router.post("/sources")
async def create_trust_source(
    payload: TrustSourceCreate,
    session: AsyncSession = Depends(get_db_session),
):
    return _columns(await service.create_trust_source(session, payload.model_dump()))


@router.post("/institutions")
async def create_institution(
    payload: InstitutionCreate,
    session: AsyncSession = Depends(get_db_session),
):
    return _columns(await service.create_institution(session, payload.model_dump()))


@router.post("/social-groups")
async def create_social_group(
    payload: SocialGroupCreate,
    session: AsyncSession = Depends(get_db_session),
):
    return _columns(await service.create_social_group(session, payload.model_dump()))


@router.post("/market-actors")
async def create_market_actor(
    payload: MarketActorCreate,
    session: AsyncSession = Depends(get_db_session),
):
    return _columns(await service.create_market_actor(session, payload.model_dump()))


service = TrustService()
