from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any, NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.farmer import Farm
from models.signals import (
    BuyerTestimonial,
    DisciplineProxy,
    FarmActivitySignal,
    InKindSettlementProof,
    Testimonial,
)
from models.verification import VerificationParticipant, VerificationSession

from repositories.exceptions import RatingOutOfRange

# The forced-choice scale is 1-4 inclusive (design doc 3.5). Named so the
# repository checks and the test assertions cannot drift apart.
MIN_RATING = 1
MAX_RATING = 4


def _check_rating(value: Any, *, field: str) -> int:
    """Reject an out-of-range rating before the database sees it.

    The tables have a CHECK constraint, so this is not the only thing standing
    between a bad value and a stored row. Doing it here as well is deliberate:
    the CHECK fires as an IntegrityError naming a Postgres constraint, which
    reads to an API caller as a 500 and leaks the constraint name. A domain
    error can be mapped to a 422, and names the field.

    The isinstance check matters as much as the range check. Without it, 2.5 or
    "3" would pass the comparison and then fail later at the database with a
    type error, so a value of the wrong *kind* slips past the check that is
    supposed to be the friendly one.
    """
    # bool is a subclass of int, and True would otherwise pass as rating=1.
    if isinstance(value, bool) or not isinstance(value, int):
        raise RatingOutOfRange(value, field=field)
    if not MIN_RATING <= value <= MAX_RATING:
        raise RatingOutOfRange(value, field=field)
    return value


class FarmerSignals(NamedTuple):
    """Everything the scoring service needs about one farmer, in one read.

    A NamedTuple rather than a dataclass so it is a plain tuple: unpackable,
    indexable, and comparable in tests without ceremony.

    Every field is a list and is empty when nothing exists, never None. The
    scoring service has to handle a farmer with only some signal types
    collected, and an empty list and a None are two different things to handle.
    Making the empty case a list means there is exactly one shape to code
    against, and "no signals yet" is a normal result rather than an error.
    """

    testimonials: Sequence[Testimonial]
    buyer_testimonials: Sequence[BuyerTestimonial]
    discipline_proxies: Sequence[DisciplineProxy]
    settlements: Sequence[InKindSettlementProof]
    farm_activity: Sequence[FarmActivitySignal]

    @property
    def is_empty(self) -> bool:
        """True when this farmer has no signals of any type."""
        return not any(
            (
                self.testimonials,
                self.buyer_testimonials,
                self.discipline_proxies,
                self.settlements,
                self.farm_activity,
            )
        )


class SignalRepository:
    """Human-sourced signals: testimony, buyer history, group discipline, settlement.

    The first three hang off verification_participants rather than off a
    farmer, because a signal is always something a specific respondent said
    about a specific farmer. Reaching the farmer means walking
    participant -> session -> farmer, which is why the queries below join twice
    rather than filtering on a farmer_id column that does not exist on the signal
    tables.

    Sessions are passed in and nothing is committed here: the caller decides the
    transaction boundary, so a whole scoring run is one unit of work.
    """

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    async def create_testimonial(
        self,
        session: AsyncSession,
        *,
        participant_id: uuid.UUID | str,
        rating: int,
        comments: str | None = None,
        personal_knowledge_flag: bool = True,
    ) -> Testimonial:
        """Record one community rating of a farmer.

        personal_knowledge_flag=False means the respondent did not know the
        farmer well enough to judge. That row is kept rather than discarded,
        because "we asked and they could not vouch" is itself a finding, but the
        scoring service excludes it from the average.
        """
        testimonial = Testimonial(
            participant_id=participant_id,
            rating=_check_rating(rating, field="rating"),
            comments=comments,
            personal_knowledge_flag=personal_knowledge_flag,
        )
        session.add(testimonial)
        await session.flush()
        return testimonial

    async def create_buyer_testimonial(
        self,
        session: AsyncSession,
        *,
        participant_id: uuid.UUID | str,
        purchase_frequency: str | None = None,
        relationship_months: int | None = None,
        avg_volume_kg: float | None = None,
        reliability_rating: int,
    ) -> BuyerTestimonial:
        """Record what a buyer says about their relationship with the farmer."""
        testimonial = BuyerTestimonial(
            participant_id=participant_id,
            purchase_frequency=purchase_frequency,
            relationship_months=relationship_months,
            avg_volume_kg=avg_volume_kg,
            reliability_rating=_check_rating(
                reliability_rating, field="reliability_rating"
            ),
        )
        session.add(testimonial)
        await session.flush()
        return testimonial

    async def create_discipline_proxy(
        self,
        session: AsyncSession,
        *,
        participant_id: uuid.UUID | str,
        social_group_id: uuid.UUID | str,
        consecutive_cycles: int | None = None,
        last_contribution_date: date | None = None,
        contribution_amount: float | None = None,
    ) -> DisciplineProxy:
        """Record a member's contribution history within a group.

        The highest-weighted character component precisely because it is dated
        and numeric rather than a character judgement (design doc 3.1, 5.3).
        """
        proxy = DisciplineProxy(
            participant_id=participant_id,
            social_group_id=social_group_id,
            consecutive_cycles=consecutive_cycles,
            last_contribution_date=last_contribution_date,
            contribution_amount=contribution_amount,
        )
        session.add(proxy)
        await session.flush()
        return proxy

    async def create_inkind_settlement(
        self,
        session: AsyncSession,
        *,
        farmer_id: uuid.UUID | str,
        counterparty_id: uuid.UUID | str | None = None,
        settlement_type: str | None = None,
        estimated_value: float | None = None,
        verification_status: str = "pending",
    ) -> InKindSettlementProof:
        """Record a repayment made in goods rather than cash.

        counterparty_id carries no foreign key: it may be a market actor, a
        trust source, or nothing at all for a plain self-report, and one column
        cannot reference three tables. It is validated at the service layer.
        """
        proof = InKindSettlementProof(
            farmer_id=farmer_id,
            counterparty_id=counterparty_id,
            settlement_type=settlement_type,
            estimated_value=estimated_value,
            verification_status=verification_status,
        )
        session.add(proof)
        await session.flush()
        return proof

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_signals_for_farmer(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> FarmerSignals:
        """Gather every signal type for one farmer.

        Five separate queries rather than one. It is a single round trip from
        the caller's point of view and one call for the scoring service, and
        keeping them separate is what lets a missing signal type be an empty list
        instead of a row of Nones. A single joined query would fan out and return
        the cross product of the tables, which is both larger and harder to
        unpick.

        The two participant-keyed signals join participant -> session to filter
        on farmer_id. Settlements carry farmer_id directly. Farm activity is
        keyed on farm_id, so the farmer's farm is resolved first - a farmer with
        no farm gets an empty list rather than an error, because a missing farm
        is legitimate and not something to raise over during a scoring run.
        """
        testimonial_stmt = (
            select(Testimonial)
            .join(
                VerificationParticipant,
                VerificationParticipant.id == Testimonial.participant_id,
            )
            .join(
                VerificationSession,
                VerificationSession.id == VerificationParticipant.session_id,
            )
            .where(VerificationSession.farmer_id == farmer_id)
            .order_by(Testimonial.created_at, Testimonial.id)
        )

        buyer_stmt = (
            select(BuyerTestimonial)
            .join(
                VerificationParticipant,
                VerificationParticipant.id == BuyerTestimonial.participant_id,
            )
            .join(
                VerificationSession,
                VerificationSession.id == VerificationParticipant.session_id,
            )
            .where(VerificationSession.farmer_id == farmer_id)
            .order_by(BuyerTestimonial.created_at, BuyerTestimonial.id)
        )

        discipline_stmt = (
            select(DisciplineProxy)
            .join(
                VerificationParticipant,
                VerificationParticipant.id == DisciplineProxy.participant_id,
            )
            .join(
                VerificationSession,
                VerificationSession.id == VerificationParticipant.session_id,
            )
            .where(VerificationSession.farmer_id == farmer_id)
            .order_by(DisciplineProxy.created_at, DisciplineProxy.id)
        )

        settlement_stmt = (
            select(InKindSettlementProof)
            .where(InKindSettlementProof.farmer_id == farmer_id)
            .order_by(InKindSettlementProof.created_at, InKindSettlementProof.id)
        )

        # Farm activity is keyed on farm_id rather than on a respondent, so it
        # joins through the farmer's farm instead of through a session.
        activity_stmt = (
            select(FarmActivitySignal)
            .join(Farm, Farm.id == FarmActivitySignal.farm_id)
            .where(Farm.farmer_id == farmer_id)
            .order_by(FarmActivitySignal.observation_date, FarmActivitySignal.id)
        )

        return FarmerSignals(
            testimonials=(await session.execute(testimonial_stmt)).scalars().all(),
            buyer_testimonials=(await session.execute(buyer_stmt)).scalars().all(),
            discipline_proxies=(await session.execute(discipline_stmt))
            .scalars()
            .all(),
            settlements=(await session.execute(settlement_stmt)).scalars().all(),
            farm_activity=(await session.execute(activity_stmt)).scalars().all(),
        )

    async def get_signals_for_social_group(
        self, session: AsyncSession, social_group_id: uuid.UUID | str
    ) -> Sequence[DisciplineProxy]:
        """Every discipline proxy recorded within one group.

        Group-level rather than per-farmer, because "how reliably does this
        chama actually meet" is a question about the group. The scoring service
        uses it to weight individual proxies by the group's own record.
        """
        stmt = (
            select(DisciplineProxy)
            .where(DisciplineProxy.social_group_id == social_group_id)
            .order_by(DisciplineProxy.created_at, DisciplineProxy.id)
        )
        return (await session.execute(stmt)).scalars().all()
