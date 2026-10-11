from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.verification import VerificationParticipant, VerificationSession
from repositories.farmer_repository import FarmerRepository
from repositories.signal_repository import SignalRepository
from repositories.trust_repository import TrustRepository
from repositories.verification_repository import VerificationRepository
from services.audit_service import AuditService


class ParticipantAlreadyRespondedError(ValueError):
    pass


class ParticipantNotFoundError(ValueError):
    pass


class PayloadMismatchError(ValueError):
    pass


class VerificationService:
    def __init__(
        self,
        verification_repository: VerificationRepository | None = None,
        signal_repository: SignalRepository | None = None,
        trust_repository: TrustRepository | None = None,
        farmer_repository: FarmerRepository | None = None,
        audit_service: AuditService | None = None,
        scoring_service: Any | None = None,
    ) -> None:
        self.verification_repository = verification_repository or VerificationRepository()
        self.signal_repository = signal_repository or SignalRepository()
        self.trust_repository = trust_repository or TrustRepository()
        self.farmer_repository = farmer_repository or FarmerRepository()
        self.audit_service = audit_service or AuditService()
        self.scoring_service = scoring_service

    async def start_verification(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> VerificationSession:
        trust_sources = await self.farmer_repository.get_trust_sources(session, farmer_id)
        market_actors = await self.trust_repository.get_market_actors_for_farmer(
            session, farmer_id
        )
        social_groups = await self.trust_repository.get_social_groups_for_farmer(
            session, farmer_id
        )
        linked = (
            [("trust_source", source.id) for source in trust_sources]
            + [("market_actor", actor.id) for actor in market_actors]
            + [("social_group", group.id) for group in social_groups]
        )

        verification_session = await self.verification_repository.create_session(
            session, farmer_id
        )
        participants = []
        for participant_type, participant_id in linked:
            participant = await self.verification_repository.create_participant(
                session, verification_session.id, participant_type, participant_id
            )
            await self.verification_repository.mark_participant_contacted(
                session, participant.id
            )
            participants.append(participant)

        await self.audit_service.write_log(
            session,
            actor_type="system",
            actor_id=None,
            action="verification_started",
            entity_type="verification_session",
            entity_id=verification_session.id,
            details={
                "participant_count": len(participants),
                "participant_count_by_type": {
                    "trust_source": len(trust_sources),
                    "market_actor": len(market_actors),
                    "social_group": len(social_groups),
                },
            },
        )
        return verification_session

    async def get_session_with_participants(
        self, session: AsyncSession, session_id: uuid.UUID | str
    ) -> tuple[VerificationSession | None, list[VerificationParticipant]]:
        verification_session = await self.verification_repository.get_session(
            session, session_id
        )
        participants = (
            await self.verification_repository.list_participants_for_session(
                session, session_id
            )
            if verification_session is not None
            else []
        )
        return verification_session, list(participants)

    async def submit_response(
        self,
        session: AsyncSession,
        session_id: uuid.UUID | str,
        participant_id: uuid.UUID | str,
        response_payload: Any,
    ) -> dict[str, Any]:
        # Get participant with row lock to prevent race conditions
        participant = await self._get_participant(session, session_id, participant_id, for_update=True)
        
        # Check payload matches participant type
        if not isinstance(response_payload, Mapping):
            raise PayloadMismatchError("Response payload must be a dictionary")
        
        payload_type = response_payload.get("participant_type")
        if payload_type != participant.participant_type:
            raise PayloadMismatchError(
                f"Payload participant_type '{payload_type}' does not match participant type '{participant.participant_type}'"
            )
        
        if participant.responded_at is not None:
            raise ParticipantAlreadyRespondedError(
                f"Participant {participant_id} has already responded"
            )

        summary_text = await self._write_signal(session, participant, response_payload)
        await self.verification_repository.record_participant_response(
            session, participant.id, summary_text
        )
        await self.audit_service.write_log(
            session,
            actor_type="participant",
            actor_id=participant.participant_id,
            action="verification_response_received",
            entity_type="verification_participant",
            entity_id=participant.id,
            details={"summary": summary_text},
        )
        return await self._finish_if_complete(session, participant.session_id, participant)

    async def mark_participant_timeout(
        self,
        session: AsyncSession,
        session_id: uuid.UUID | str,
        participant_id: uuid.UUID | str,
    ) -> dict[str, Any]:
        # Get participant with row lock to prevent race conditions
        participant = await self._get_participant(session, session_id, participant_id, for_update=True)
        if participant.responded_at is not None:
            raise ParticipantAlreadyRespondedError(
                f"Participant {participant_id} has already been resolved"
            )
        await self.verification_repository.mark_participant_timeout(
            session, participant.id
        )
        await self.audit_service.write_log(
            session,
            actor_type="system",
            actor_id=None,
            action="verification_participant_timed_out",
            entity_type="verification_participant",
            entity_id=participant.id,
            details={"summary": "timeout"},
        )
        return await self._finish_if_complete(session, participant.session_id, participant)

    async def create_settlement(
        self, session: AsyncSession, farmer_id: uuid.UUID | str, data: dict[str, Any]
    ):
        proof = await self.signal_repository.create_inkind_settlement(
            session, farmer_id=farmer_id, **data
        )
        await self.audit_service.write_log(
            session,
            actor_type="officer",
            actor_id=None,
            action="settlement_proof_created",
            entity_type="in_kind_settlement_proof",
            entity_id=proof.id,
        )
        return proof

    async def _get_participant(
        self,
        session: AsyncSession,
        session_id: uuid.UUID | str,
        participant_id: uuid.UUID | str,
        for_update: bool = False,
    ) -> VerificationParticipant:
        # Use a direct query with row lock to prevent race conditions
        stmt = (
            select(VerificationParticipant)
            .where(
                VerificationParticipant.id == participant_id,
                VerificationParticipant.session_id == session_id,
            )
        )
        
        if for_update:
            stmt = stmt.with_for_update()
            
        result = await session.execute(stmt)
        participant = result.scalar_one_or_none()
        
        if participant is None:
            raise ParticipantNotFoundError(
                f"Participant {participant_id} was not found in session {session_id}"
            )
        return participant

    async def _write_signal(
        self,
        session: AsyncSession,
        participant: VerificationParticipant,
        payload: Any,
    ) -> str:
        if participant.participant_type == "trust_source":
            rating = _payload_value(payload, "rating")
            if _payload_value(payload, "personal_knowledge_flag", True) is False:
                return "no_personal_knowledge"
            await self.signal_repository.create_testimonial(
                session,
                participant_id=participant.id,
                rating=rating,
                comments=_payload_value(payload, "comments"),
                personal_knowledge_flag=True,
            )
            return f"rating={rating}"
        if participant.participant_type == "market_actor":
            reliability = _payload_value(payload, "reliability_rating")
            await self.signal_repository.create_buyer_testimonial(
                session,
                participant_id=participant.id,
                purchase_frequency=_payload_value(payload, "purchase_frequency"),
                relationship_months=_payload_value(payload, "relationship_months"),
                avg_volume_kg=_payload_value(payload, "avg_volume_kg"),
                reliability_rating=reliability,
            )
            return f"reliability={reliability}"
        if participant.participant_type == "social_group":
            cycles = _payload_value(payload, "consecutive_cycles")
            await self.signal_repository.create_discipline_proxy(
                session,
                participant_id=participant.id,
                social_group_id=_payload_value(
                    payload, "social_group_id", participant.participant_id
                ),
                consecutive_cycles=cycles,
                last_contribution_date=_payload_value(payload, "last_contribution_date"),
                contribution_amount=_payload_value(payload, "contribution_amount"),
            )
            return f"{cycles}_cycles"
        raise ValueError(f"Unsupported participant type: {participant.participant_type}")

    async def _finish_if_complete(
        self,
        session: AsyncSession,
        session_id: uuid.UUID | str,
        participant: VerificationParticipant,
    ) -> dict[str, Any]:
        participants = await self.verification_repository.list_participants_for_session(
            session, session_id
        )
        complete = all(item.responded_at is not None for item in participants)
        score_result = None
        session_status = "in_progress"
        if complete:
            from services.scoring_service import ScoringService, InsufficientDataError

            scorer = self.scoring_service or ScoringService()
            compute_score = getattr(scorer, "compute_score", None)
            if compute_score is None:
                raise RuntimeError("ScoringService.compute_score is not available yet")
            verification_session = await self.verification_repository.get_session(
                session, session_id
            )
            if verification_session is None:
                raise ParticipantNotFoundError(
                    f"Verification session {session_id} was not found"
                )
            
            try:
                score_result = await compute_score(
                    session, verification_session.farmer_id
                )
                session_status = "completed"
            except InsufficientDataError:
                # Handle case where no scoreable signals exist (all participants timed out or said "no personal knowledge")
                score_result = None
                await self.verification_repository.update_session_status(
                    session, session_id, "insufficient_data"
                )
                session_status = "insufficient_data"
        return {
            "participant_status": participant.response,
            "session_status": session_status,
            "score_result": score_result,
        }


def _payload_value(payload: Any, name: str, default: Any = None) -> Any:
    if isinstance(payload, Mapping):
        return payload.get(name, default)
    return getattr(payload, name, default)
