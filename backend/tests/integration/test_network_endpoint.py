"""The `/farmers/{id}/network` endpoint against a real Postgres.

This guards the exact failure the UI hit: the endpoint named repository methods
that did not exist (`get_farmer_market_actors`, `get_farmer_social_groups`,
`get_latest_session`) and read `latest_session.participants`, a relationship the
model does not define. None of those fail for a farmer that does not exist, so
the old placeholder test (which only asserted 404) never reached them.

The endpoint coroutine is called directly with the test session, then its dict
is validated through the production response model. That exercises both the
broken calls and the schema (including the nullable verifier columns) without
standing up the app against the wrong database. Every row is rolled back.

Which database, and when this refuses to run, is decided in db_target.py.
"""

import contextlib
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.section13 import get_farmer_network
from core.database import _asyncpg_url, _ssl_connect_args
from models.farmer import Farm, Farmer
from models.loan import Loan
from repositories.trust_repository import TrustRepository
from repositories.verification_repository import VerificationRepository
from schemas.network import NetworkResponse

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


def _farmer() -> Farmer:
    tag = uuid.uuid4().hex
    return Farmer(
        full_name="Grace Wambui",
        national_id=f"NET-{tag}",
        phone=f"+2547{tag[:8]}",
        gender="female",
        location="Nakuru",
        county="Nakuru",
    )


async def _network(farmer_id, session) -> NetworkResponse:
    payload = await get_farmer_network(farmer_id, session=session)
    return NetworkResponse.model_validate(payload)


async def test_network_redraws_a_farmer_with_all_three_verifier_kinds():
    """Farmer, farm, one of each verifier, and a session with a participant."""
    trust = TrustRepository()
    verification = VerificationRepository()

    async with db() as Session:
        async with Session() as s:
            farmer = _farmer()
            s.add(farmer)
            await s.flush()

            farm = Farm(
                farmer_id=farmer.id,
                acreage=2.5,
                production_type="Crop",
                latitude=-0.3031,
                longitude=36.08,
            )
            s.add(farm)
            await s.flush()

            source = await trust.create_trust_source(
                s, {"full_name": "Kariuki", "category": "chief"}
            )
            actor = await trust.create_market_actor(
                s, {"name": "Nakuru Grain", "actor_type": None}
            )
            group = await trust.create_social_group(
                s, {"name": "Mwangaza", "group_type": None}
            )
            await trust.link_farmer_trust_source(s, farmer.id, source.id)
            await trust.link_farmer_market_actor(s, farmer.id, actor.id)
            await trust.link_farmer_social_group(s, farmer.id, group.id)

            session_row = await verification.create_session(s, farmer.id)
            participant = await verification.create_participant(
                s, session_row.id, "trust_source", source.id
            )
            await verification.mark_participant_contacted(s, participant.id)

            network = await _network(farmer.id, s)

            assert network.farmer["id"] == str(farmer.id)
            assert [item.id for item in network.farms] == [farm.id]

            assert [item.name for item in network.trust_sources] == ["Kariuki"]
            assert [item.name for item in network.market_actors] == ["Nakuru Grain"]
            assert [item.name for item in network.social_groups] == ["Mwangaza"]

            # Nullable columns survive the response instead of 500ing.
            assert network.market_actors[0].actor_type is None
            assert network.social_groups[0].group_type is None

            latest = network.latest_session
            assert latest is not None
            assert latest.id == session_row.id
            assert len(latest.participants) == 1
            assert latest.participants[0].id == participant.id
            assert latest.participants[0].participant_type == "trust_source"
            assert latest.participants[0].participant_id == source.id
            assert latest.participants[0].responded is None

            assert network.current_score is None
            assert network.loans == []

            await s.rollback()


async def test_network_has_no_session_for_a_farmer_never_verified():
    """`latest_session` is null, not a crash, before the first round."""
    async with db() as Session:
        async with Session() as s:
            farmer = _farmer()
            s.add(farmer)
            await s.flush()

            network = await _network(farmer.id, s)

            assert network.latest_session is None
            assert network.loans == []
            assert network.farms == []

            await s.rollback()


async def test_latest_session_is_the_most_recent_one():
    """Two sessions: the network uses the one that started last."""
    verification = VerificationRepository()

    async with db() as Session:
        async with Session() as s:
            farmer = _farmer()
            s.add(farmer)
            await s.flush()

            older = await verification.create_session(
                s, farmer.id, status="completed"
            )
            newer = await verification.create_session(s, farmer.id)
            # server_default now() is the same within one transaction, so
            # pin distinct clocks instead of relying on the id tiebreak.
            older.started_at = datetime(2026, 3, 1, tzinfo=timezone.utc)
            newer.started_at = datetime(2026, 3, 2, tzinfo=timezone.utc)
            await s.flush()

            network = await _network(farmer.id, s)

            assert network.latest_session is not None
            assert network.latest_session.id == newer.id
            assert network.latest_session.id != older.id

            await s.rollback()


async def test_a_farmer_with_a_loan_reports_the_application_date():
    """`applied_at` is the loan's own column, not the row's `created_at`."""
    async with db() as Session:
        async with Session() as s:
            farmer = _farmer()
            s.add(farmer)
            await s.flush()

            loan = Loan(
                farmer_id=farmer.id,
                amount=5000,
                status="pending",
                applied_at=datetime(2026, 3, 4, tzinfo=timezone.utc),
            )
            s.add(loan)
            await s.flush()

            network = await _network(farmer.id, s)

            assert len(network.loans) == 1
            assert network.loans[0].id == loan.id
            assert network.loans[0].status == "pending"
            assert network.loans[0].applied_at is not None
            assert network.loans[0].applied_at.date() == date(2026, 3, 4)

            await s.rollback()
