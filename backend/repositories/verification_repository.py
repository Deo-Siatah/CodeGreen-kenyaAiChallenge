"""Verification sessions and the participants contacted during one.

Ported from VerificationSessionRepository and the session-scoped half of
VerificationRepository / ParticipantResponseRepository.

Behaviour deliberately preserved from Cypher:
  * `list_participants_for_session` keeps ORDER BY created_at ASC. The Cypher
    `get_all_by_session` had that ORDER BY, so it is the one ordering guarantee
    in the original that had to survive the port.
  * ids are generated in Python;
  * a missing row is None / an empty sequence, never an exception.

Dropped because the relational schema has nowhere to put them — see the gap
list in the handover notes: session.farmer_name, session.final_score,
session.decision, participant.participant_name, participant.participant_phone,
and the per-question response list (the table has one `response` text column,
not a list).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.verification import VerificationParticipant, VerificationSession

# The statuses the Cypher update_status treated as terminal by stamping
# completed_at. Preserved verbatim so the two implementations agree on when a
# session stops being in progress.
_TERMINAL_STATUSES = frozenset({"complete", "timeout"})


class VerificationRepository:
    """Stateless: the session is supplied per call."""

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def create_session(
        self,
        session: AsyncSession,
        farmer_id: uuid.UUID | str,
        *,
        status: str = "pending",
        demo_mode: bool = False,
        expires_at: datetime | None = None,
    ) -> VerificationSession:
        obj = VerificationSession(
            farmer_id=farmer_id,
            status=status,
            demo_mode=demo_mode,
            expires_at=expires_at,
        )
        session.add(obj)
        await session.flush()
        return obj

    async def get_session(
        self, session: AsyncSession, session_id: uuid.UUID | str
    ) -> VerificationSession | None:
        return await session.get(VerificationSession, session_id)

    async def get_participant(
        self, session: AsyncSession, participant_id: uuid.UUID | str
    ) -> VerificationParticipant | None:
        return await session.get(VerificationParticipant, participant_id)

    async def update_session_status(
        self,
        session: AsyncSession,
        session_id: uuid.UUID | str,
        status: str,
    ) -> VerificationSession | None:
        """Move a session to a new status, stamping completed_at on completion.

        Ported from the Cypher `update_status`. Two behaviours preserved from it:
        completed_at is set only for the terminal statuses, and is left alone
        otherwise (so a session that is re-opened does not lose its completion
        time); and a missing session is None rather than an error.

        The Cypher version also accepted final_score and decision and coalesced
        them onto the session. Neither is a column on verification_sessions, so
        that data cannot be stored; the score for a session is derivable from the
        farmer's current score_profiles row. See the gap list.
        """
        obj = await session.get(VerificationSession, session_id)
        if obj is None:
            return None
        obj.status = status
        if status in _TERMINAL_STATUSES:
            obj.completed_at = func.now()
        await session.flush()
        return obj

    # ------------------------------------------------------------------
    # Participants
    # ------------------------------------------------------------------

    async def create_participant(
        self,
        session: AsyncSession,
        session_id: uuid.UUID | str,
        participant_type: str,
        participant_id: uuid.UUID | str,
    ) -> VerificationParticipant:
        """Attach one respondent to a session, returning the participant either way.

        Idempotent on (session_id, participant_type, participant_id), which is
        the table's unique constraint. The Cypher version always created, but it
        had no such constraint to violate; here an unguarded INSERT would turn a
        retried request into a 500, so ON CONFLICT DO NOTHING is used.

        Under DO NOTHING, RETURNING yields no row when the insert was skipped,
        which is exactly the signal needed to tell the two cases apart: the
        RETURNING id is present iff we inserted, and its absence means the row
        already existed. So the SELECT is only paid on the conflict path, and
        the caller always gets a participant back rather than having to decide
        whether to go looking for one.
        """
        values = {
            "session_id": session_id,
            "participant_type": participant_type,
            "participant_id": participant_id,
        }
        result = await session.execute(
            pg_insert(VerificationParticipant)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=[
                    VerificationParticipant.session_id,
                    VerificationParticipant.participant_type,
                    VerificationParticipant.participant_id,
                ]
            )
            .returning(VerificationParticipant.id)
        )
        inserted_id = result.scalar_one_or_none()
        if inserted_id is not None:
            # A Core insert does not populate the identity map, so the ORM
            # object still has to be loaded.
            participant = await session.get(VerificationParticipant, inserted_id)
            if participant is not None:  # pragma: no cover - just inserted
                return participant

        existing = await session.execute(
            select(VerificationParticipant).where(
                VerificationParticipant.session_id == session_id,
                VerificationParticipant.participant_type == participant_type,
                VerificationParticipant.participant_id == participant_id,
            )
        )
        return existing.scalar_one()

    async def mark_participant_contacted(
        self, session: AsyncSession, participant_id: uuid.UUID | str
    ) -> VerificationParticipant | None:
        """Stamp contacted_at. Idempotent: re-contacting keeps the first stamp.

        Keyed on the participant row's own id. The Cypher `mark_as_received`
        looked rows up by (session_id, participant_phone), and phone is not a
        column on verification_participants.
        """
        result = await session.execute(
            select(VerificationParticipant).where(
                VerificationParticipant.id == participant_id
            )
        )
        participant = result.scalar_one_or_none()
        if participant is None:
            return None
        if participant.contacted_at is None:
            # func.now() rather than datetime.now(UTC) so the timestamp comes
            # from the same clock as every other server_default in the schema.
            participant.contacted_at = func.now()
            await session.flush()
        return participant

    async def record_participant_response(
        self,
        session: AsyncSession,
        participant_id: uuid.UUID | str,
        response: str,
    ) -> VerificationParticipant | None:
        """Store the respondent's answer and stamp responded_at.

        Overwrites any previous answer. The Cypher `add_response` appended to a
        list of per-question answers; verification_participants has a single
        `response` text column, so multi-question accumulation needs its own
        table before this can be faithful.
        """
        result = await session.execute(
            select(VerificationParticipant).where(
                VerificationParticipant.id == participant_id
            )
        )
        participant = result.scalar_one_or_none()
        if participant is None:
            return None
        participant.response = response
        participant.responded_at = func.now()
        await session.flush()
        return participant

    async def mark_participant_timeout(
        self, session: AsyncSession, participant_id: uuid.UUID | str
    ) -> VerificationParticipant | None:
        participant = await session.get(VerificationParticipant, participant_id)
        if participant is None:
            return None
        participant.response = "timeout"
        participant.responded_at = func.now()
        await session.flush()
        return participant

    async def list_participants_for_session(
        self, session: AsyncSession, session_id: uuid.UUID | str
    ) -> Sequence[VerificationParticipant]:
        """Participants in contact order — the ORDER BY created_at ASC that the
        Cypher `get_all_by_session` guaranteed. id is the tiebreak so rows
        created in one transaction keep a stable relative order."""
        stmt = (
            select(VerificationParticipant)
            .where(VerificationParticipant.session_id == session_id)
            .order_by(
                VerificationParticipant.created_at.asc(),
                VerificationParticipant.id.asc(),
            )
        )
        result = await session.execute(stmt)
        return result.scalars().all()
