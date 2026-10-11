"""Transaction-semantics tests for the SQL repositories.

These need a real Postgres, because the behaviour under test *is* Postgres
behaviour: `ON CONFLICT DO NOTHING`, unique-violation errors, foreign-key
enforcement, and `FOR UPDATE` serialisation. A mock could only assert that the
code *asks* for ON CONFLICT; it could not show that the row that comes back is
the one that was already there. SQLite is no help either - it has neither
ON CONFLICT nor the same constraint timing.

Which database this runs against, and when it refuses to run, is decided in
db_target.py.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import delete, insert, pool, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import _asyncpg_url, _ssl_connect_args
from models.farmer import Farmer
from models.links import FarmerTrustSourceLink
from models.scoring import ScoreProfile
from models.trust import TrustSource
from models.verification import VerificationParticipant
from repositories.scoring_repository import ScoringRepository
from repositories.trust_repository import TrustRepository
from repositories.verification_repository import VerificationRepository

from db_target import TEST_URL, skip_marker

pytestmark = skip_marker()

_URL = TEST_URL or ""


@asynccontextmanager
async def db():
    """A session factory on a throwaway engine.

    NullPool so every session gets its own server connection. That is what lets
    the concurrency test have two genuinely separate transactions, and it also
    means a test can never inherit session state from a previous one.
    """
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
    """A farmer with collision-proof unique columns."""
    tag = uuid.uuid4().hex
    return Farmer(
        full_name="Test Farmer",
        national_id=f"NA-{tag}",
        phone=f"+2547{tag[:8]}",
        gender="female",
        location="Testville",
    )


async def test_concurrent_scoring_yields_versions_1_and_2():
    """Two scorers running at once must not both believe they are version 1.

    create_score_profile takes SELECT ... FOR UPDATE on the farmer row before
    reading MAX(version), so the two transactions serialise on that row and the
    second one sees the first one's insert. Without the lock both would read an
    empty table, both would write version 1, and the partial unique index would
    reject one of them with a UniqueViolation instead of a clean sequential
    history.

    This is the one test that cannot roll back. FOR UPDATE only serialises across
    *committed* transactions: if both sessions left their work uncommitted, the
    second would block forever on the first's lock and the test would hang
    rather than pass. So the two scoring transactions commit, and the rows are
    removed explicitly in the cleanup step. The single-current-profile
    assertion is checked before that cleanup runs.
    """
    repo = ScoringRepository()
    async with db() as Session:
        async with Session() as s:
            farmer = _farmer()
            s.add(farmer)
            await s.commit()
            farmer_id = farmer.id

        async def score() -> int:
            async with Session() as s:
                profile = await repo.create_score_profile(
                    s,
                    farmer_id,
                    character_score=50.0,
                    capacity_score=50.0,
                    final_score=50.0,
                )
                await s.commit()
                return profile.version

        try:
            # Bounded so a regression that reintroduces the race fails as a
            # timeout instead of hanging the suite.
            versions = await asyncio.wait_for(
                asyncio.gather(score(), score()), timeout=60
            )
            assert sorted(versions) == [1, 2], f"got versions {versions}"

            async with Session() as s:
                current = (
                    (
                        await s.execute(
                            select(ScoreProfile).where(
                                ScoreProfile.farmer_id == farmer_id,
                                ScoreProfile.is_current.is_(True),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(current) == 1, f"{len(current)} current profiles"

            async with Session() as s:
                assert (await repo.get_current_score(s, farmer_id)) is not None
        finally:
            # CASCADE removes the score_profiles rows with the farmer.
            async with Session() as s:
                await s.execute(delete(Farmer).where(Farmer.id == farmer_id))
                await s.commit()


async def test_duplicate_participant_raises_then_repository_returns_existing():
    """The unique constraint is the arbiter; the repository is the polite path.

    A raw duplicate INSERT has to fail, or nothing is enforcing the constraint.
    But the repository call for the same identity has to come back with the row
    that is already there rather than raising, because the same respondent being
    contacted twice is a normal retry, not a bug worth a 500.
    """
    repo = VerificationRepository()
    async with db() as Session:
        async with Session() as s:
            farmer = _farmer()
            s.add(farmer)
            await s.flush()

            session_row = await repo.create_session(s, farmer.id)
            participant_id = uuid.uuid4()
            first = await repo.create_participant(
                s, session_row.id, "trust_source", participant_id
            )

            # begin_nested() is a SAVEPOINT: without it the unique violation
            # would abort the whole transaction and nothing after it could run.
            with pytest.raises(IntegrityError):
                async with s.begin_nested():
                    await s.execute(
                        insert(VerificationParticipant).values(
                            session_id=session_row.id,
                            participant_type="trust_source",
                            participant_id=participant_id,
                        )
                    )

            second = await repo.create_participant(
                s, session_row.id, "trust_source", participant_id
            )
            assert second.id == first.id
            assert second.participant_id == participant_id

            await s.rollback()


async def test_duplicate_link_is_idempotent_and_missing_fk_still_raises():
    """ON CONFLICT DO NOTHING is for duplicates, not for a blanket ignore.

    Linking the same farmer to the same trust source twice must be a no-op that
    returns the original row. But a link to a farmer that does not exist has to
    still fail: swallowing that would create an orphaned edge that nothing ever
    joins back from, and the FK exists precisely to prevent it.
    """
    repo = TrustRepository()
    async with db() as Session:
        async with Session() as s:
            farmer = _farmer()
            source = TrustSource(full_name="Chief", category="chief")
            s.add_all([farmer, source])
            await s.flush()

            first = await repo.link_farmer_trust_source(
                s, farmer.id, source.id, relationship_type="neighbour"
            )
            second = await repo.link_farmer_trust_source(
                s, farmer.id, source.id, relationship_type="neighbour"
            )
            # No single-column id to compare: the link's identity is the
            # composite PK (farmer_id, trust_source_id).
            assert (second.farmer_id, second.trust_source_id) == (
                first.farmer_id,
                first.trust_source_id,
            )

            with pytest.raises(IntegrityError):
                async with s.begin_nested():
                    await repo.link_farmer_trust_source(
                        s, uuid.uuid4(), source.id, relationship_type="stranger"
                    )

            links = (
                (
                    await s.execute(
                        select(FarmerTrustSourceLink).where(
                            FarmerTrustSourceLink.farmer_id == farmer.id
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(links) == 1

            await s.rollback()


async def test_second_score_demotes_the_first_and_rollback_leaves_nothing():
    """A recomputation supersedes, never overwrites - and rolls back clean.

    Score history is append-only so a loan officer can see how a score moved
    (design doc 3.4), so the first profile is demoted to is_current=false rather
    than updated. The second half of the test then proves the transaction really
    was rolled back, by counting the rows again from a fresh connection.
    """
    repo = ScoringRepository()
    async with db() as Session:
        async with Session() as s:
            farmer = _farmer()
            s.add(farmer)
            await s.flush()
            farmer_id = farmer.id

            first = await repo.create_score_profile(
                s, farmer_id, character_score=40.0, capacity_score=40.0, final_score=40.0
            )
            second = await repo.create_score_profile(
                s, farmer_id, character_score=70.0, capacity_score=70.0, final_score=70.0
            )
            assert (first.version, second.version) == (1, 2)

            await s.refresh(first)
            assert first.is_current is False
            assert first.character_score == 40.0, "history must not be overwritten"
            assert second.is_current is True

            current = await repo.get_current_score(s, farmer_id)
            assert current.id == second.id
            assert [p.version for p in await repo.get_score_history(s, farmer_id)] == [
                2,
                1,
            ]

            await s.rollback()

        async with Session() as s:
            remaining = (
                (
                    await s.execute(
                        select(ScoreProfile).where(ScoreProfile.farmer_id == farmer_id)
                    )
                )
                .scalars()
                .all()
            )
            assert remaining == [], f"rollback left {len(remaining)} rows behind"
