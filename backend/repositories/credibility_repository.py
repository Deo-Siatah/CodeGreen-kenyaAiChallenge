"""Verifier credibility: the evolving track record that replaces static
category weights (design doc 5.1).

No Cypher predecessor existed — the frontend's verifier list was mock data
because nothing fed it. This is new.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.credibility import VerifierCredibility

# TODO: finalize credibility formula.
#
# CREDIBILITY SCORE
# ----------------
#     score = 1 + 0.5 * (repaid_count - defaulted_count)
#                  / (repaid_count + defaulted_count + 5)
#
#   1.0  Neutral. phase2.md 5.1 states a new verifier "starts neutral (1.0) for
#        a new verifier, drifts up or down as their past endorsees repay or
#        default", so a verifier with nothing on the record scores exactly 1.0
#        and applies no penalty to their first endorsements.
#
#   0.5  The coefficient. It sets how far a verifier's history can move their
#        weight, and it is what keeps credibility influential but never
#        decisive: 1.5x is the largest single multiplier in the scoring
#        formula, so the other components still decide the outcome. A verifier
#        with a long clean record can double the pull of their testimony, but
#        cannot carry a farmer across a threshold on their own.
#
#   +5   The damping, and the reason there is no clamp. This is not a throwaway
#        constant: it is what bounds the score. As the record grows the
#        ratio saturates, so the score approaches 1 + 0.5 = 1.5 with only
#        repayments and 1 - 0.5 = 0.5 with only defaults, and the denominator
#        can never reach zero so a new verifier is always defined. The
#        observable range is therefore (0.5, 1.5) - open, because the limits
#        are only ever approached, never reached. The earlier version needed an
#        explicit clamp because 1.0 + (r - d) / (r + d + 1) is unbounded; the
#        0.5 coefficient is what made the clamp unnecessary, and a smaller
#        damping term (say +1) would have saturated immediately, pinning every
#        verifier with even one clean endorsement at the ceiling.
#
#   Trade-off of damping: credibility is slow to respond early and slow to
#   recover. (1, 0) is only 1.083, not 1.5, so a verifier cannot build
#   credibility in one lucky endorsement - or lose it in one default.
#
# This function is the only place the arithmetic lives, and both callers go
# through it, so replacing it later means editing one function.
CREDIBILITY_NEUTRAL = 1.0
# Asymptotic limits, not clamps: the formula cannot reach them. Asserted as an
# invariant by the unit tests rather than enforced at runtime.
CREDIBILITY_FLOOR = 0.5
CREDIBILITY_CEILING = 1.5


def _credibility_score(repaid_count: int, defaulted_count: int) -> float:
    return 1.0 + 0.5 * (repaid_count - defaulted_count) / (
        repaid_count + defaulted_count + 5
    )


class CredibilityRepository:
    """Stateless: the session is supplied per call."""

    async def get_or_create_credibility(
        self, session: AsyncSession, subject_type: str, subject_id: uuid.UUID | str
    ) -> VerifierCredibility:
        """Fetch a verifier's track record, creating a neutral one if absent.

        Idempotent via ON CONFLICT DO NOTHING on the unique (subject_type, subject_id):
        a plain SELECT-then-INSERT races, and two concurrent first endorsements
        would collide on that unique index.
        """
        await session.execute(
            pg_insert(VerifierCredibility)
            .values(
                subject_type=subject_type,
                subject_id=subject_id,
                total_endorsements=0,
                repaid_count=0,
                defaulted_count=0,
                credibility_score=CREDIBILITY_NEUTRAL,
            )
            .on_conflict_do_nothing(
                index_elements=[VerifierCredibility.subject_type, VerifierCredibility.subject_id]
            )
        )
        await session.flush()

        result = await session.execute(
            select(VerifierCredibility).where(
                VerifierCredibility.subject_type == subject_type,
                VerifierCredibility.subject_id == subject_id
            )
        )
        return result.scalar_one()

    async def update_credibility_on_loan_outcome(
        self,
        session: AsyncSession,
        subject_type: str,
        subject_id: uuid.UUID | str,
        *,
        repaid: bool,
    ) -> VerifierCredibility:
        """Record a loan outcome against the verifier who endorsed that farmer.

        Increments repaid_count or defaulted_count, then recomputes
        credibility_score.

        The row is locked FOR UPDATE before the counters are touched, so two
        concurrent loan settlements for the same verifier cannot both read the
        old counts and lose one increment. The recompute happens in Python rather
        than as SQL arithmetic on the row, because the formula is a placeholder
        that is going to change and one function should own it.
        """
        result = await session.execute(
            select(VerifierCredibility)
            .where(
                VerifierCredibility.subject_type == subject_type,
                VerifierCredibility.subject_id == subject_id
            )
            .with_for_update()
        )
        credibility = result.scalar_one_or_none()
        if credibility is None:
            # No track record yet: start one rather than dropping the outcome on
            # the floor, since the endorsement itself is the first data point.
            credibility = await self.get_or_create_credibility(
                session, subject_type, subject_id
            )

        if repaid:
            credibility.repaid_count += 1
            credibility.total_endorsements += 1
        else:
            credibility.defaulted_count += 1
            credibility.total_endorsements += 1

        credibility.credibility_score = _credibility_score(
            credibility.repaid_count, credibility.defaulted_count
        )
        await session.flush()
        return credibility
