from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.signals import FarmActivitySignal

# The only source that writes automatically today. Anything else means a human
# or a different pipeline asserted crop continuity, and the scoring service
# weights the sources differently, so it is a column rather than a constant.
DEFAULT_SOURCE = "sentinel2"


class FarmActivityRepository:
    """Third-party observation of a plot: NDVI and cultivation continuity.

    The only signal with no human respondent, and structurally the hardest to
    fabricate (design doc 2.3.3) - which is why it is kept in its own module
    rather than folded into SignalRepository. It is keyed on farm_id, not on a
    verification participant, and it is written by a scheduled pipeline on its
    own cadence rather than in response to a verification session.
    """

    async def create_farm_activity_signal(
        self,
        session: AsyncSession,
        *,
        farm_id: uuid.UUID | str,
        ndvi_value: float | None = None,
        cultivation_continuity_score: float | None = None,
        observation_date: date,
        source: str = DEFAULT_SOURCE,
    ) -> FarmActivitySignal:
        """Record one observation of a farm.

        observation_date is required rather than defaulted to today: these rows
        are historical observations arriving from a pipeline, and defaulting the
        date would silently misfile a backfill as if it were seen now. Two
        observations of the same farm on the same date are allowed - the
        pipeline may revise a reading, and the history is append-only.
        """
        signal = FarmActivitySignal(
            farm_id=farm_id,
            ndvi_value=ndvi_value,
            cultivation_continuity_score=cultivation_continuity_score,
            observation_date=observation_date,
            source=source,
        )
        session.add(signal)
        await session.flush()
        return signal

    async def get_latest_for_farm(
        self, session: AsyncSession, farm_id: uuid.UUID | str
    ) -> FarmActivitySignal | None:
        """The most recent observation, or None if the farm has never been seen.

        Ordered by observation_date with id as the tiebreak rather than relying
        on insertion order: a backfilled row inserted yesterday but observed
        months ago is not the latest reading, and created_at would call it one.
        """
        stmt = (
            select(FarmActivitySignal)
            .where(FarmActivitySignal.farm_id == farm_id)
            .order_by(
                FarmActivitySignal.observation_date.desc(),
                FarmActivitySignal.id.desc(),
            )
            .limit(1)
        )
        return (await session.execute(stmt)).scalars().first()

    async def get_activity_history(
        self,
        session: AsyncSession,
        farm_id: uuid.UUID | str,
        since_date: date | None = None,
    ) -> Sequence[FarmActivitySignal]:
        """Observations oldest-first, optionally only those from since_date.

        Ascending because this feeds a trend calculation: a caller summing
        recent values or looking for a change between the first and last
        observation should not have to sort. since_date is inclusive, so
        "the last 12 months" is passed as the first day of the window rather
        than the day before it.
        """
        stmt = select(FarmActivitySignal).where(FarmActivitySignal.farm_id == farm_id)
        if since_date is not None:
            stmt = stmt.where(FarmActivitySignal.observation_date >= since_date)
        stmt = stmt.order_by(
            FarmActivitySignal.observation_date, FarmActivitySignal.id
        )
        return (await session.execute(stmt)).scalars().all()
