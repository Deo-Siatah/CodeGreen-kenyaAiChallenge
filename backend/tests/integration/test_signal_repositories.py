"""Signal repositories against a real Postgres.

Two things here cannot be checked without a database:

  * the two-layer rating guard - the Python check and the DB CHECK constraint
    are separate mechanisms, and the point is to prove BOTH reject a bad value.
    A test that only exercises the Python check proves nothing about the CHECK,
    and a test that only exercises the CHECK proves nothing about the
    domain error the API is meant to return. So each bypasses one layer on
    purpose: raw SQL with a bad rating to hit the constraint, and a bypass of
    the Python check to hit the validator.
  * the ordering of get_activity_history, and the empty-signal shape, which are
    only meaningful against real rows.

Which database, and when this refuses to run, is decided in db_target.py. Every
test rolls back.
"""

import contextlib
import uuid
from datetime import date

import pytest
from sqlalchemy import insert, pool, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import _asyncpg_url, _ssl_connect_args
from models.farmer import Farm, Farmer
# Aliased on import because pytest tries to collect a class named Testimonial
# as a test case; Test_ is its prefix convention.
from models.signals import BuyerTestimonial
from models.signals import Testimonial as TestimonialRow
from models.trust import SocialGroup
from repositories.exceptions import RatingOutOfRange
from repositories.farm_activity_repository import FarmActivityRepository
from repositories.signal_repository import SignalRepository
from repositories.trust_repository import TrustRepository
from repositories.verification_repository import VerificationRepository

from db_target import TEST_URL, skip_marker

pytestmark = skip_marker()

_URL = TEST_URL or ""


@contextlib.asynccontextmanager
async def db():
    """A session factory on a throwaway engine. NullPool, so no shared state."""
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
        full_name="Signal Test Farmer",
        national_id=f"NA-{tag}",
        phone=f"+2547{tag[:8]}",
        gender="female",
        location="Testville",
    )


async def _session_for(s, farmer, *, participant_type="trust_source"):
    """A farmer with one verification session and one participant.

    Most signals hang off a participant, so almost every test needs this shape
    first. participant_id has no FK of its own - the table documents that the
    service layer validates it against participant_type - so the participant
    here points at a real trust source to keep the data coherent.
    """
    source = await TrustRepository().create_trust_source(
        s, {"full_name": "Chief", "category": "chief"}
    )
    farmer_row = _farmer()
    s.add(farmer_row)
    await s.flush()
    vrepo = VerificationRepository()
    session_row = await vrepo.create_session(s, farmer_row.id)
    participant = await vrepo.create_participant(
        s, session_row.id, participant_type, source.id
    )
    return farmer_row, session_row, participant


# ---------------------------------------------------------------------------
# create_* round-trips
# ---------------------------------------------------------------------------


async def test_create_testimonial_round_trips():
    repo = SignalRepository()
    async with db() as Session:
        async with Session() as s:
            _, _, participant = await _session_for(s, _farmer())
            row = await repo.create_testimonial(
                s,
                participant_id=participant.id,
                rating=4,
                comments="Reliable, repaid on time.",
                personal_knowledge_flag=True,
            )
            await s.refresh(row)
            assert row.id is not None
            assert row.rating == 4
            assert row.comments == "Reliable, repaid on time."
            assert row.personal_knowledge_flag is True
            assert row.participant_id == participant.id
            await s.rollback()


async def test_create_buyer_testimonial_round_trips():
    repo = SignalRepository()
    async with db() as Session:
        async with Session() as s:
            _, _, participant = await _session_for(s, _farmer())
            row = await repo.create_buyer_testimonial(
                s,
                participant_id=participant.id,
                purchase_frequency="weekly",
                relationship_months=18,
                avg_volume_kg=250.5,
                reliability_rating=3,
            )
            await s.refresh(row)
            assert (row.purchase_frequency, row.relationship_months) == (
                "weekly",
                18,
            )
            assert row.avg_volume_kg == 250.5
            assert row.reliability_rating == 3
            await s.rollback()


async def test_create_discipline_proxy_round_trips():
    repo = SignalRepository()
    async with db() as Session:
        async with Session() as s:
            _, _, participant = await _session_for(s, _farmer())
            group = SocialGroup(name="Kamande Chama", group_type="chama")
            s.add(group)
            await s.flush()
            row = await repo.create_discipline_proxy(
                s,
                participant_id=participant.id,
                social_group_id=group.id,
                consecutive_cycles=6,
                last_contribution_date=date(2026, 8, 31),
                contribution_amount=1500.0,
            )
            await s.refresh(row)
            assert row.consecutive_cycles == 6
            assert row.last_contribution_date == date(2026, 8, 31)
            assert row.contribution_amount == 1500.0
            assert row.social_group_id == group.id
            await s.rollback()


async def test_create_inkind_settlement_round_trips():
    repo = SignalRepository()
    async with db() as Session:
        async with Session() as s:
            farmer, _, _ = await _session_for(s, _farmer())
            row = await repo.create_inkind_settlement(
                s,
                farmer_id=farmer.id,
                counterparty_id=uuid.uuid4(),
                settlement_type="maize",
                estimated_value=400.0,
                verification_status="pending",
            )
            await s.refresh(row)
            assert row.farmer_id == farmer.id
            assert row.settlement_type == "maize"
            assert row.estimated_value == 400.0
            assert row.verification_status == "pending"
            await s.rollback()


async def test_create_farm_activity_signal_round_trips_with_default_source():
    repo = FarmActivityRepository()
    async with db() as Session:
        async with Session() as s:
            farmer, _, _ = await _session_for(s, _farmer())
            farm = Farm(farmer_id=farmer.id, acreage=2.5, production_type="maize")
            s.add(farm)
            await s.flush()
            row = await repo.create_farm_activity_signal(
                s,
                farm_id=farm.id,
                ndvi_value=0.7231,
                cultivation_continuity_score=88.5,
                observation_date=date(2026, 7, 15),
            )
            await s.refresh(row)
            assert row.ndvi_value == 0.7231
            assert row.cultivation_continuity_score == 88.5
            assert row.observation_date == date(2026, 7, 15)
            assert row.source == "sentinel2", "the default must be applied"
            await s.rollback()


# ---------------------------------------------------------------------------
# The two rating layers, checked independently
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [0, 5, -1, 99])
async def test_python_layer_rejects_bad_testimonial_rating(bad):
    """Layer 1: the domain exception, before any SQL is emitted."""
    repo = SignalRepository()
    async with db() as Session:
        async with Session() as s:
            _, _, participant = await _session_for(s, _farmer())
            with pytest.raises(RatingOutOfRange):
                await repo.create_testimonial(
                    s, participant_id=participant.id, rating=bad
                )
            await s.rollback()


@pytest.mark.parametrize("bad", [0, 5, -1, 99])
async def test_python_layer_rejects_bad_reliability_rating(bad):
    repo = SignalRepository()
    async with db() as Session:
        async with Session() as s:
            _, _, participant = await _session_for(s, _farmer())
            with pytest.raises(RatingOutOfRange):
                await repo.create_buyer_testimonial(
                    s, participant_id=participant.id, reliability_rating=bad
                )
            await s.rollback()


@pytest.mark.parametrize("bad", [0, 5])
async def test_database_layer_also_rejects_bad_rating(bad):
    """Layer 2: the CHECK constraint, with the Python check bypassed entirely.

    Raw INSERT, not the repository. If the CHECK were missing or wrong, the
    repository tests above would still pass and a bad rating would reach
    production through any other write path - a data fix, an admin query, a
    future service that forgets the validator.
    """
    async with db() as Session:
        async with Session() as s:
            _, _, participant = await _session_for(s, _farmer())
            with pytest.raises(IntegrityError) as excinfo:
                async with s.begin_nested():
                    await s.execute(
                        insert(TestimonialRow).values(
                            participant_id=participant.id, rating=bad
                        )
                    )
            # Named, so a constraint that was renamed or dropped is visible in
            # the failure rather than looking like any other IntegrityError.
            assert "rating_between_1_and_4" in str(excinfo.value)
            await s.rollback()


@pytest.mark.parametrize("bad", [0, 5])
async def test_database_layer_also_rejects_bad_reliability_rating(bad):
    async with db() as Session:
        async with Session() as s:
            _, _, participant = await _session_for(s, _farmer())
            with pytest.raises(IntegrityError) as excinfo:
                async with s.begin_nested():
                    await s.execute(
                        insert(BuyerTestimonial).values(
                            participant_id=participant.id, reliability_rating=bad
                        )
                    )
            assert "reliability_rating_between_1_and_4" in str(excinfo.value)
            await s.rollback()


async def test_both_layers_agree_on_the_boundary():
    """1 and 4 are valid; 0 and 5 are not. Both layers must agree on where.

    The forced-choice scale has no neutral midpoint, so a validator that
    accepted 0 as "unrated" or 5 as "very good" would be a scoring bug: a 0
    would drag an average down and a 5 would inflate it past the top of the
    scale.
    """
    repo = SignalRepository()
    async with db() as Session:
        async with Session() as s:
            _, _, participant = await _session_for(s, _farmer())
            for good in (1, 4):
                row = await repo.create_testimonial(
                    s, participant_id=participant.id, rating=good
                )
                assert row.rating == good
            for bad in (0, 5):
                with pytest.raises(RatingOutOfRange):
                    await repo.create_testimonial(
                        s, participant_id=participant.id, rating=bad
                    )
                with pytest.raises(IntegrityError):
                    async with s.begin_nested():
                        await s.execute(
                            insert(TestimonialRow).values(
                                participant_id=participant.id, rating=bad
                            )
                        )
            await s.rollback()


# ---------------------------------------------------------------------------
# get_signals_for_farmer
# ---------------------------------------------------------------------------


async def test_get_signals_for_farmer_with_no_signals_is_empty_not_an_error():
    """The case the scoring service has to handle first.

    A farmer mid-onboarding has a session but no testimony yet. That must come
    back as five empty lists, not an exception and not a result full of Nones -
    the scoring service should be able to read every field unconditionally.
    """
    repo = SignalRepository()
    async with db() as Session:
        async with Session() as s:
            farmer, _, _ = await _session_for(s, _farmer())
            signals = await repo.get_signals_for_farmer(s, farmer.id)

            assert signals.is_empty is True
            assert signals.testimonials == []
            assert signals.buyer_testimonials == []
            assert signals.discipline_proxies == []
            assert signals.settlements == []
            assert signals.farm_activity == []
            for field in type(signals)._fields:
                assert getattr(signals, field) is not None
            await s.rollback()


async def test_get_signals_for_farmer_gathers_every_type():
    """All five populated at once, each reached by its own join path.

    Also proves the walk is correct in both directions: signals belonging to a
    *different* farmer must not leak in, which a wrong join on participant_id
    alone would allow.
    """
    signals_repo = SignalRepository()
    activity_repo = FarmActivityRepository()
    async with db() as Session:
        async with Session() as s:
            farmer, _, participant = await _session_for(s, _farmer())
            other, _, other_participant = await _session_for(s, _farmer())

            group = SocialGroup(name="Chama", group_type="chama")
            s.add(group)
            await s.flush()
            farm = Farm(farmer_id=farmer.id, acreage=1.0)
            s.add(farm)
            await s.flush()

            await signals_repo.create_testimonial(
                s, participant_id=participant.id, rating=3
            )
            await signals_repo.create_buyer_testimonial(
                s, participant_id=participant.id, reliability_rating=2
            )
            await signals_repo.create_discipline_proxy(
                s, participant_id=participant.id, social_group_id=group.id
            )
            await signals_repo.create_inkind_settlement(s, farmer_id=farmer.id)
            await activity_repo.create_farm_activity_signal(
                s, farm_id=farm.id, observation_date=date(2026, 6, 1)
            )
            # Belongs to the other farmer; must not appear below.
            await signals_repo.create_testimonial(
                s, participant_id=other_participant.id, rating=4
            )

            signals = await signals_repo.get_signals_for_farmer(s, farmer.id)

            assert len(signals.testimonials) == 1
            assert signals.testimonials[0].rating == 3
            assert len(signals.buyer_testimonials) == 1
            assert len(signals.discipline_proxies) == 1
            assert len(signals.settlements) == 1
            assert len(signals.farm_activity) == 1
            assert signals.is_empty is False
            assert other.id != farmer.id
            await s.rollback()


async def test_get_signals_for_farmer_with_no_farm_returns_empty_activity():
    """No farm is legitimate, so activity is empty rather than a failure."""
    repo = SignalRepository()
    async with db() as Session:
        async with Session() as s:
            farmer, _, participant = await _session_for(s, _farmer())
            await repo.create_testimonial(s, participant_id=participant.id, rating=2)

            signals = await repo.get_signals_for_farmer(s, farmer.id)
            assert signals.farm_activity == []
            assert len(signals.testimonials) == 1
            assert signals.is_empty is False
            await s.rollback()


# ---------------------------------------------------------------------------
# Farm activity reads
# ---------------------------------------------------------------------------


async def test_get_activity_history_is_ascending_by_observation_date():
    """Oldest first, so a trend calculation can use the ends directly."""
    repo = FarmActivityRepository()
    async with db() as Session:
        async with Session() as s:
            farmer, _, _ = await _session_for(s, _farmer())
            farm = Farm(farmer_id=farmer.id, acreage=1.0)
            s.add(farm)
            await s.flush()

            # Inserted out of order on purpose: insertion order is not
            # observation order, and a backfill arrives late.
            for day, ndvi in ((date(2026, 3, 1), 0.4), (date(2026, 6, 1), 0.7), (date(2026, 1, 1), 0.2)):
                await repo.create_farm_activity_signal(
                    s, farm_id=farm.id, ndvi_value=ndvi, observation_date=day
                )

            history = await repo.get_activity_history(s, farm.id)
            dates = [row.observation_date for row in history]
            assert dates == sorted(dates), f"not ascending: {dates}"
            assert dates == [date(2026, 1, 1), date(2026, 3, 1), date(2026, 6, 1)]
            assert [row.ndvi_value for row in history] == [0.2, 0.4, 0.7]
            await s.rollback()


async def test_get_activity_history_since_date_is_inclusive():
    repo = FarmActivityRepository()
    async with db() as Session:
        async with Session() as s:
            farmer, _, _ = await _session_for(s, _farmer())
            farm = Farm(farmer_id=farmer.id, acreage=1.0)
            s.add(farm)
            await s.flush()
            for day in (date(2026, 1, 1), date(2026, 5, 1), date(2026, 9, 1)):
                await repo.create_farm_activity_signal(
                    s, farm_id=farm.id, observation_date=day
                )

            history = await repo.get_activity_history(
                s, farm.id, since_date=date(2026, 5, 1)
            )
            assert [row.observation_date for row in history] == [
                date(2026, 5, 1),
                date(2026, 9, 1),
            ]
            await s.rollback()


async def test_get_latest_for_farm_picks_the_observation_date_not_the_insert():
    """A backfilled row is not the latest reading, even if inserted last."""
    repo = FarmActivityRepository()
    async with db() as Session:
        async with Session() as s:
            farmer, _, _ = await _session_for(s, _farmer())
            farm = Farm(farmer_id=farmer.id, acreage=1.0)
            s.add(farm)
            await s.flush()
            await repo.create_farm_activity_signal(
                s, farm_id=farm.id, observation_date=date(2026, 8, 1)
            )
            # Backfill: older observation, inserted afterwards.
            await repo.create_farm_activity_signal(
                s, farm_id=farm.id, observation_date=date(2025, 8, 1)
            )

            latest = await repo.get_latest_for_farm(s, farm.id)
            assert latest is not None
            assert latest.observation_date == date(2026, 8, 1)
            await s.rollback()


async def test_get_latest_for_farm_with_no_observations_is_none():
    repo = FarmActivityRepository()
    async with db() as Session:
        async with Session() as s:
            farmer, _, _ = await _session_for(s, _farmer())
            farm = Farm(farmer_id=farmer.id, acreage=1.0)
            s.add(farm)
            await s.flush()
            assert await repo.get_latest_for_farm(s, farm.id) is None
            assert await repo.get_activity_history(s, farm.id) == []
            await s.rollback()


# ---------------------------------------------------------------------------
# Foreign keys
# ---------------------------------------------------------------------------


async def test_settlement_for_a_farmer_that_does_not_exist_raises_foreign_key():
    """The FK must still bite now that a real repository writes this table.

    Before this section the only path raised NotImplementedError, so nothing
    ever attempted the insert and the constraint was untested. A settlement
    pointing at no farmer is an orphan: it would never show up in any farmer's
    signals, so it would be invisible rather than wrong.
    """
    repo = SignalRepository()
    async with db() as Session:
        async with Session() as s:
            with pytest.raises(IntegrityError) as excinfo:
                await repo.create_inkind_settlement(
                    s, farmer_id=uuid.uuid4(), settlement_type="maize"
                )
            assert "farmer_id" in str(excinfo.value) or "farmers" in str(
                excinfo.value
            )
            await s.rollback()


async def test_rollback_leaves_nothing_behind():
    """Every test above rolls back; this proves it rather than assuming it."""
    repo = SignalRepository()
    async with db() as Session:
        async with Session() as s:
            farmer, _, participant = await _session_for(s, _farmer())
            await repo.create_testimonial(s, participant_id=participant.id, rating=4)
            farmer_id, participant_id = farmer.id, participant.id
            # Detached after the rollback below, so read the ids now: an expired
            # attribute on a closed session raises DetachedInstanceError.
            await s.rollback()

        async with Session() as s:
            signals = await repo.get_signals_for_farmer(s, farmer_id)
            assert signals.is_empty is True
            assert signals.testimonials == []
            count = (
                await s.execute(
                    text("select count(*) from testimonials where participant_id = :p"),
                    {"p": participant_id},
                )
            ).scalar_one()
            assert count == 0
            await s.rollback()
