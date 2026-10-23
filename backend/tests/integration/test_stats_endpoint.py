import contextlib
import uuid

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.section13 import get_farmers
from api.stats import get_stats_overview
from core.database import _asyncpg_url, _ssl_connect_args
from models.farmer import Farm, Farmer
from models.scoring import ScoreProfile
from schemas.farmers import FarmersListResponse

from db_target import TEST_URL, skip_marker

pytestmark = skip_marker()

_URL = TEST_URL or ""


@contextlib.asynccontextmanager
async def db():
    engine = create_async_engine(
        _asyncpg_url(_URL, "TEST_DATABASE_URL_DIRECT"),
        poolclass=pool.NullPool,
        connect_args=_ssl_connect_args(_URL, "TEST_DATABASE_URL_DIRECT"),
    )
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


def _farmer(name: str) -> Farmer:
    tag = uuid.uuid4().hex
    return Farmer(
        full_name=name,
        national_id=f"STAT-{tag}",
        phone=f"+2547{tag[:8]}",
        gender="female",
        location="Nakuru",
        county="Nakuru",
    )


async def test_stats_overview_validates_and_portfolio_includes_unscored_farmers():
    async with db() as Session:
        async with Session() as session:
            scored = _farmer("Scored Demo Farmer")
            unscored = _farmer("Unscored Demo Farmer")
            session.add_all([scored, unscored])
            await session.flush()

            session.add(
                Farm(
                    farmer_id=scored.id,
                    acreage=2.0,
                    latitude=-0.3,
                    longitude=36.1,
                )
            )
            session.add(
                ScoreProfile(
                    farmer_id=scored.id,
                    version=1,
                    character_score=80.0,
                    capacity_score=70.0,
                    final_score=76.0,
                    decision="ELIGIBLE",
                    recommended_amount=5000.0,
                    is_current=True,
                )
            )
            await session.flush()

            overview = await get_stats_overview(session=session)
            assert overview.farmers.total >= 1
            assert overview.scores.scored >= 1
            assert any(case.id == scored.id for case in overview.recent_cases)

            listing = FarmersListResponse.model_validate(
                await get_farmers(limit=100, offset=0, session=session)
            )
            ids = {item.id for item in listing.items}
            assert scored.id in ids
            assert unscored.id in ids
            assert listing.total >= len(listing.items)

            await session.rollback()
