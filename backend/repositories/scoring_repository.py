"""Score profiles and the explainability component rows that back one score.

The important behaviour here is in create_score_profile: score_profiles carries
a partial unique index (UNIQUE (farmer_id) WHERE is_current) added in the
initial migration, and that index is what enforces "a farmer has exactly one
current score". Recomputation therefore has to retire the old current row in the
*same transaction* as it inserts the new one — if the insert committed first, or
if the demotion were left to a separate transaction, the index would reject it.

Ported from ScoreRepository.create_score_profile, which was a bare
`CREATE (s:ScoreProfile) SET s += $data`. That version had no is_current
handling at all, so the demotion below is new and required by the index rather
than copied from Cypher.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.farmer import Farmer
from models.scoring import ScoreComponent, ScoreProfile


class ScoringRepository:
    """Stateless: the session is supplied per call."""

    async def create_score_profile(
        self,
        session: AsyncSession,
        farmer_id: uuid.UUID | str,
        *,
        character_score: float,
        capacity_score: float | None,
        final_score: float,
        decision: str | None = None,
        recommended_amount: float | None = None,
        computed_at=None,
        version: int | None = None,
    ) -> ScoreProfile:
        """Record a scoring run as the farmer's new current profile.

        Three steps, all in the caller's transaction, in this order:
          1. lock the farmer row;
          2. demote any existing current profile to is_current = false;
          3. insert the new is_current = true row.

        Step 1 is not redundant with step 2. The partial unique index would
        already reject a second concurrent INSERT, but it would reject it with an
        error rather than making the second writer wait and then succeed.
        Locking the parent farmer row serialises concurrent recomputations for
        the same farmer, so the loser waits and then finds the winner's row
        already demoted. (SELECT ... FOR UPDATE on the score_profiles row itself
        would not help: when no current profile exists yet there is no row to
        lock.)
        """
        # 1. Serialise all score writes for this farmer.
        await session.execute(
            select(Farmer.id).where(Farmer.id == farmer_id).with_for_update()
        )

        # 2. Retire the previous current profile. Guarded on is_current so only
        #    the one row the index points at is touched, not the whole history.
        await session.execute(
            update(ScoreProfile)
            .where(
                ScoreProfile.farmer_id == farmer_id,
                ScoreProfile.is_current.is_(True),
            )
            .values(is_current=False)
        )

        if version is None:
            # ScoreProfile is append-only by design (models/scoring.py), so a
            # recomputation appends the next version rather than overwriting.
            # The column has a Python-side default of 1, which would give every
            # profile version 1 and make the history useless.
            previous_max = await session.execute(
                select(func.max(ScoreProfile.version)).where(
                    ScoreProfile.farmer_id == farmer_id
                )
            )
            version = (previous_max.scalar_one() or 0) + 1

        # 3. Insert the new current profile.
        profile = ScoreProfile(
            farmer_id=farmer_id,
            version=version,
            character_score=character_score,
            capacity_score=capacity_score,
            final_score=final_score,
            decision=decision,
            recommended_amount=recommended_amount,
            is_current=True,
        )
        if computed_at is not None:
            profile.computed_at = computed_at
        session.add(profile)
        await session.flush()
        return profile

    async def get_current_score(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> ScoreProfile | None:
        stmt = select(ScoreProfile).where(
            ScoreProfile.farmer_id == farmer_id,
            ScoreProfile.is_current.is_(True),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_score_components(
        self, session: AsyncSession, score_profile_id: uuid.UUID | str
    ) -> Sequence[ScoreComponent]:
        """Return the persisted structured breakdown for one profile."""
        result = await session.execute(
            select(ScoreComponent)
            .where(ScoreComponent.score_profile_id == score_profile_id)
            .order_by(ScoreComponent.id)
        )
        return result.scalars().all()

    async def get_score_history(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> Sequence[ScoreProfile]:
        """Every profile for a farmer, newest version first.

        No Cypher predecessor existed, so there is no ordering to preserve; this
        is the natural reading order for a version history and makes
        `history[0]` the current score.
        """
        stmt = (
            select(ScoreProfile)
            .where(ScoreProfile.farmer_id == farmer_id)
            .order_by(ScoreProfile.version.desc(), ScoreProfile.id)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def create_score_components(
        self,
        session: AsyncSession,
        score_profile_id: uuid.UUID | str,
        components: list[dict[str, Any]],
    ) -> Sequence[ScoreComponent]:
        """Bulk-insert one score's full component breakdown.

        `axis` and `component_name` carry the CHECK constraint on axis; an
        invalid value is rejected by the database here, which is the point of
        writing the whole breakdown on every score.
        """
        if not components:
            return []
        payload = [{"score_profile_id": score_profile_id, **c} for c in components]
        # ORM bulk insert by execute-many: one round trip, not one per row.
        await session.execute(insert(ScoreComponent), payload)
        await session.flush()

        stmt = (
            select(ScoreComponent)
            .where(ScoreComponent.score_profile_id == score_profile_id)
            .order_by(ScoreComponent.id)
        )
        rows = await session.execute(stmt)
        return rows.scalars().all()
