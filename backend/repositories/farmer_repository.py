"""Farmer and farm persistence (SQLAlchemy 2.0 async).

Every method takes the AsyncSession as its first argument rather than opening
one, for two reasons: a caller can compose several repository calls into a
single transaction, and a test can open one transaction, exercise the code and
roll it back instead of cleaning up rows afterwards.

Ported from the Cypher FarmerRepository. Behaviour preserved:
  * ids are generated here, not by the database, so a caller gets a usable id
    back from the create call;
  * a missing row is None (the Cypher `result.single()` returned None too).

Not carried over: `get_trust_sources`, which the Cypher class exposed but this
section did not specify. See the gap list in the handover notes.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.farmer import Farm, Farmer
from models.links import FarmerTrustSourceLink
from models.trust import TrustSource


class FarmerRepository:
    """Stateless by design: the session is supplied per call, so a single
    instance is safe to share for the life of the app."""

    async def create_farmer(
        self, session: AsyncSession, farmer_data: dict[str, Any]
    ) -> Farmer:
        farmer = Farmer(**farmer_data)
        session.add(farmer)
        # flush, never commit: the caller owns the transaction boundary. This
        # still hands back a populated primary key, and it surfaces a unique
        # violation on national_id/phone here rather than at the caller's commit.
        await session.flush()
        return farmer

    async def get_farmer(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> Farmer | None:
        return await session.get(Farmer, farmer_id)

    async def get_farmer_for_scoring(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> dict[str, Any] | None:
        """Load only the scoring-safe farmer projection.

        This method is for sessions from get_scoring_session(), whose role can
        read the view but must not read the farmers base table or gender.
        """
        result = await session.execute(
            text(
                """
                SELECT id, full_name, national_id, phone, date_of_birth,
                       location, village, sub_county, county, farming_type,
                       years_farming, created_at, updated_at
                FROM farmers_scoring_safe
                WHERE id = :farmer_id
                """
            ),
            {"farmer_id": farmer_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def list_farmers(self, session: AsyncSession) -> Sequence[Farmer]:
        # The Cypher version had no ORDER BY, so it had no order at all. Newest
        # first is the useful default for an admin list; id is the tiebreak so
        # the ordering is total and pagination stays stable.
        stmt = select(Farmer).order_by(Farmer.created_at.desc(), Farmer.id)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def create_farm(
        self, session: AsyncSession, farm_data: dict[str, Any]
    ) -> Farm:
        farm = Farm(**farm_data)
        session.add(farm)
        await session.flush()
        return farm

    async def get_farm_by_farmer_id(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> Sequence[Farm]:
        """All farms owned by one farmer.

        The name is singular, but farms.farmer_id is not unique — a farmer may
        own several plots — so this returns every one of them rather than
        arbitrarily picking a first. Change the name if a single-farm
        assumption is actually what callers need.
        """
        stmt = (
            select(Farm)
            .where(Farm.farmer_id == farmer_id)
            .order_by(Farm.created_at.desc(), Farm.id)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_trust_sources(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> Sequence[TrustSource]:
        """Everyone who has vouched for this farmer.

        Ported from the Cypher `get_trust_sources`, which walked
        (farmer)-[:VERIFIED_BY]->(source). That relationship is now the
        farmer_trust_source_links join table, and the edge carried no ORDER BY,
        so there is no ordering to preserve; full_name is used so the order is at
        least total.
        """
        stmt = (
            select(TrustSource)
            .join(
                FarmerTrustSourceLink,
                FarmerTrustSourceLink.trust_source_id == TrustSource.id,
            )
            .where(FarmerTrustSourceLink.farmer_id == farmer_id)
            .order_by(TrustSource.full_name, TrustSource.id)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_farmers_paginated(
        self, session: AsyncSession, limit: int, offset: int
    ) -> tuple[Sequence[tuple[Farmer, Any]], int]:
        """Get paginated list of farmers with their current score profile.
        
        Returns:
            A tuple of (farmers_with_scores, total_count)
        """
        from models.scoring import ScoreProfile
        
        # Get total count
        count_stmt = select(text("count(*)")).select_from(Farmer)
        count_result = await session.execute(count_stmt)
        total = count_result.scalar()
        
        # Get paginated farmers with their current score
        stmt = (
            select(Farmer, ScoreProfile)
            .outerjoin(
                ScoreProfile,
                ScoreProfile.farmer_id == Farmer.id,
            )
            .where(ScoreProfile.is_current == True)
            .order_by(Farmer.created_at.desc(), Farmer.id)
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return result.all(), total

    async def get_farms(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> Sequence[Farm]:
        """Get all farms for a farmer."""
        stmt = (
            select(Farm)
            .where(Farm.farmer_id == farmer_id)
            .order_by(Farm.created_at.desc(), Farm.id)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
