from sqlalchemy.ext.asyncio import AsyncSession

from models.signals import BuyerTestimonial, InKindSettlementProof
from models.trust import Institution, MarketActor, SocialGroup, TrustSource
from repositories.signal_repository import SignalRepository
from repositories.trust_repository import TrustRepository
from services.audit_service import AuditService


# The only disagreement left between the request schemas and the tables.
#
#   trust_sources.name          -> full_name
#   institutions.institution_type -> type
#
# There is no drop-and-warn list any more. The Trust*Create schemas are
# extra="forbid" and carry only fields that have a column, so by the time a
# payload reaches here every key maps to a real column. A key that does not is
# now a caller bug and is left to raise from the ORM rather than being silently
# discarded - a silently dropped field is exactly how a client ends up believing
# it stored something it did not.
_RENAMES = {
    TrustSource: {"name": "full_name"},
    Institution: {"institution_type": "type"},
}


def _to_columns(entity: type, data: dict) -> dict:
    """Apply the renames. Everything else is already a column name."""
    renames = _RENAMES.get(entity, {})
    return {renames.get(key, key): value for key, value in data.items()}


class TrustService:
    """Creates the four trust-network entities.

    The session is passed in by the caller and the caller owns the commit.
    """

    def __init__(self, audit_service: AuditService | None = None):
        self.repository = TrustRepository()
        self.signal_repository = SignalRepository()
        self.audit_service = audit_service or AuditService()

    # Trust Sources

    async def create_trust_source(
        self, session: AsyncSession, data: dict
    ) -> TrustSource:
        obj = await self.repository.create_trust_source(
            session, _to_columns(TrustSource, data)
        )
        await self.audit_service.write_log(
            session, "officer", None, "trust_source_created", "trust_source", obj.id
        )
        return obj

    # Institutions

    async def create_institution(
        self, session: AsyncSession, data: dict
    ) -> Institution:
        obj = await self.repository.create_institution(
            session, _to_columns(Institution, data)
        )
        await self.audit_service.write_log(
            session, "officer", None, "institution_created", "institution", obj.id
        )
        return obj

    # Social Groups

    async def create_social_group(
        self, session: AsyncSession, data: dict
    ) -> SocialGroup:
        obj = await self.repository.create_social_group(
            session, _to_columns(SocialGroup, data)
        )
        await self.audit_service.write_log(
            session, "officer", None, "social_group_created", "social_group", obj.id
        )
        return obj

    # Market Actors

    async def create_market_actor(self, session: AsyncSession, data: dict) -> MarketActor:
        obj = await self.repository.create_market_actor(
            session, _to_columns(MarketActor, data)
        )
        await self.audit_service.write_log(
            session, "officer", None, "market_actor_created", "market_actor", obj.id
        )
        return obj

    async def link_trust_source(self, session: AsyncSession, farmer_id, trust_source_id, **context):
        return await self.repository.link_farmer_trust_source(
            session, farmer_id, trust_source_id, **context
        )

    async def link_institution(self, session: AsyncSession, farmer_id, institution_id, **context):
        return await self.repository.link_farmer_institution(
            session, farmer_id, institution_id, **context
        )

    async def link_social_group(self, session: AsyncSession, farmer_id, social_group_id, **context):
        return await self.repository.link_farmer_social_group(
            session, farmer_id, social_group_id, **context
        )

    async def link_market_actor(self, session: AsyncSession, farmer_id, market_actor_id, **context):
        return await self.repository.link_farmer_market_actor(
            session, farmer_id, market_actor_id, **context
        )

    # Buyer Testimonials

    async def create_buyer_testimonial(
        self, session: AsyncSession, data: dict
    ) -> BuyerTestimonial:
        """Pass-through to SignalRepository.

        No scoring logic here: this section only moves the write path onto SQL.
        Note the payload keys are the column names already, so there is no
        rename map to apply - the schemas for these endpoints are the ones the
        Cypher layer was built around.
        """
        obj = await self.signal_repository.create_buyer_testimonial(session, **data)
        await self.audit_service.write_log(
            session,
            "officer",
            None,
            "buyer_testimonial_created",
            "buyer_testimonial",
            obj.id,
        )
        return obj

    # In-Kind Settlement Proofs

    async def create_settlement_proof(
        self, session: AsyncSession, data: dict
    ) -> InKindSettlementProof:
        obj = await self.signal_repository.create_inkind_settlement(session, **data)
        await self.audit_service.write_log(
            session,
            "officer",
            None,
            "settlement_proof_created",
            "in_kind_settlement_proof",
            obj.id,
        )
        return obj
