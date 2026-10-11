"""Trust-network entities and the farmer <-> entity link rows.

Consolidates what used to be five Cypher repositories (TrustSourceRepository,
InstitutionRepository, SocialGroupRepository, MarketActorRepository and the
farmer-link half of RelationshipRepository) into one class, because in the
relational schema they are all "create a row, then relate it to a farmer".

Behaviour preserved from Cypher:
  * ids are generated in Python, not by the database;
  * the link methods were MERGE, i.e. already idempotent, and stay idempotent
    here via ON CONFLICT DO NOTHING.

The extra context columns on the link tables (relationship_type, years_known,
membership_type, role, ...) have no Cypher equivalent — the graph edges carried
no properties — so they are new, optional, keyword-only arguments.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.links import (
    FarmerInstitutionLink,
    FarmerMarketActorLink,
    FarmerSocialGroupLink,
    FarmerTrustSourceLink,
)
from models.trust import Institution, MarketActor, SocialGroup, TrustSource


class TrustRepository:
    """Stateless: the session is supplied per call."""

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    async def get_trust_source(
        self, session: AsyncSession, trust_source_id: uuid.UUID | str
    ) -> TrustSource | None:
        """Fetch one trust source, or None if there is no such row.

        Ported from the Cypher TrustSourceRepository.get_by_id, which returned
        result.single() and so already returned None for a miss. Named
        get_trust_source rather than get_by_id to match create_trust_source in
        this same class now that the two have been consolidated.
        """
        return await session.get(TrustSource, trust_source_id)

    async def get_market_actor(
        self, session: AsyncSession, market_actor_id: uuid.UUID | str
    ) -> MarketActor | None:
        """Fetch one market actor, or None if there is no such row."""
        return await session.get(MarketActor, market_actor_id)

    async def create_trust_source(
        self, session: AsyncSession, trust_source_data: dict[str, Any]
    ) -> TrustSource:
        obj = TrustSource(**trust_source_data)
        session.add(obj)
        await session.flush()
        return obj

    async def create_institution(
        self, session: AsyncSession, institution_data: dict[str, Any]
    ) -> Institution:
        obj = Institution(**institution_data)
        session.add(obj)
        await session.flush()
        return obj

    async def create_social_group(
        self, session: AsyncSession, group_data: dict[str, Any]
    ) -> SocialGroup:
        obj = SocialGroup(**group_data)
        session.add(obj)
        await session.flush()
        return obj

    async def create_market_actor(
        self, session: AsyncSession, actor_data: dict[str, Any]
    ) -> MarketActor:
        obj = MarketActor(**actor_data)
        session.add(obj)
        await session.flush()
        return obj

    async def get_social_groups_for_farmer(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> list[SocialGroup]:
        result = await session.execute(
            select(SocialGroup)
            .join(
                FarmerSocialGroupLink,
                FarmerSocialGroupLink.social_group_id == SocialGroup.id,
            )
            .where(FarmerSocialGroupLink.farmer_id == farmer_id)
        )
        return list(result.scalars().all())

    async def get_market_actors_for_farmer(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> list[MarketActor]:
        result = await session.execute(
            select(MarketActor)
            .join(
                FarmerMarketActorLink,
                FarmerMarketActorLink.market_actor_id == MarketActor.id,
            )
            .where(FarmerMarketActorLink.farmer_id == farmer_id)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Links
    # ------------------------------------------------------------------

    async def _upsert_link(
        self,
        session: AsyncSession,
        model: type,
        key_columns: tuple[ColumnElement[Any], ...],
        key_values: dict[str, Any],
        context: dict[str, Any],
    ) -> Any:
        """Insert a link row, or return the existing one if it is already there.

        ON CONFLICT DO NOTHING rather than a check-then-insert, because the
        check-then-insert version races: two concurrent requests both see no
        row and one of them then takes a unique-violation error. Letting the
        database arbitrate keeps this idempotent under retry, which matters
        because the Cypher MERGE it replaces was also idempotent.
        """
        values = {**key_values, **context}
        stmt = (
            pg_insert(model)
            .values(**values)
            .on_conflict_do_nothing(index_elements=list(key_columns))
        )
        await session.execute(stmt)
        await session.flush()

        # RETURNING cannot be used to distinguish "inserted" from "already
        # there" under DO NOTHING (it yields no row on conflict), so re-read
        # the row. This is the row the caller should see either way.
        lookup = select(model).where(
            *(column == values[column.key] for column in key_columns)
        )
        result = await session.execute(lookup)
        return result.scalar_one_or_none()

    async def link_farmer_trust_source(
        self,
        session: AsyncSession,
        farmer_id: uuid.UUID | str,
        trust_source_id: uuid.UUID | str,
        *,
        relationship_type: str | None = None,
        years_known: int | None = None,
    ) -> FarmerTrustSourceLink:
        return await self._upsert_link(
            session,
            FarmerTrustSourceLink,
            (FarmerTrustSourceLink.farmer_id, FarmerTrustSourceLink.trust_source_id),
            {"farmer_id": farmer_id, "trust_source_id": trust_source_id},
            {"relationship_type": relationship_type, "years_known": years_known},
        )

    async def link_farmer_institution(
        self,
        session: AsyncSession,
        farmer_id: uuid.UUID | str,
        institution_id: uuid.UUID | str,
        *,
        membership_type: str | None = None,
        joined_date=None,
    ) -> FarmerInstitutionLink:
        return await self._upsert_link(
            session,
            FarmerInstitutionLink,
            (
                FarmerInstitutionLink.farmer_id,
                FarmerInstitutionLink.institution_id,
            ),
            {"farmer_id": farmer_id, "institution_id": institution_id},
            {"membership_type": membership_type, "joined_date": joined_date},
        )

    async def link_farmer_social_group(
        self,
        session: AsyncSession,
        farmer_id: uuid.UUID | str,
        social_group_id: uuid.UUID | str,
        *,
        role: str | None = None,
        joined_date=None,
    ) -> FarmerSocialGroupLink:
        return await self._upsert_link(
            session,
            FarmerSocialGroupLink,
            (
                FarmerSocialGroupLink.farmer_id,
                FarmerSocialGroupLink.social_group_id,
            ),
            {"farmer_id": farmer_id, "social_group_id": social_group_id},
            {"role": role, "joined_date": joined_date},
        )

    async def link_farmer_market_actor(
        self,
        session: AsyncSession,
        farmer_id: uuid.UUID | str,
        market_actor_id: uuid.UUID | str,
        *,
        relationship_type: str | None = None,
        since_date=None,
    ) -> FarmerMarketActorLink:
        return await self._upsert_link(
            session,
            FarmerMarketActorLink,
            (
                FarmerMarketActorLink.farmer_id,
                FarmerMarketActorLink.market_actor_id,
            ),
            {"farmer_id": farmer_id, "market_actor_id": market_actor_id},
            {"relationship_type": relationship_type, "since_date": since_date},
        )
