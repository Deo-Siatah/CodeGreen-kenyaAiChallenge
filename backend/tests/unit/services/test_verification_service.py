import contextlib
import uuid

import pytest
from sqlalchemy import pool, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import _asyncpg_url, _ssl_connect_args
from models import signals
from models.verification import VerificationParticipant
from repositories.trust_repository import TrustRepository
from services.farmer_service import FarmerService
from services.trust_service import TrustService
from services.verification_service import (
    ParticipantAlreadyRespondedError,
    VerificationService,
)
from tests.integration.db_target import TEST_URL, skip_marker

pytestmark = skip_marker()
_URL = TEST_URL or ""


@contextlib.asynccontextmanager
async def db():
    engine = create_async_engine(
        _asyncpg_url(_URL, "TEST_DATABASE_URL_DIRECT"),
        poolclass=pool.NullPool,
        connect_args=_ssl_connect_args(_URL, "TEST_DATABASE_URL_DIRECT"),
    )
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


def farmer_values() -> dict:
    tag = uuid.uuid4().hex
    return {
        "full_name": "Verification Farmer",
        "national_id": f"VF-{tag}",
        "phone": f"+2547{tag[:8]}",
        "gender": "female",
        "location": "Testville",
    }


async def arrange(session):
    farmer = await FarmerService().create_farmer(session, farmer_values())
    trust_source = await TrustService().create_trust_source(
        session, {"name": "Chief", "category": "chief", "location": "Testville"}
    )
    market_actor = await TrustService().create_market_actor(
        session, {"name": "Buyer", "actor_type": "buyer", "location": "Testville"}
    )
    social_group = await TrustService().create_social_group(
        session, {"name": "Chama", "group_type": "sacco", "location": "Testville"}
    )
    trust_repository = TrustRepository()
    await trust_repository.link_farmer_trust_source(
        session, farmer.id, trust_source.id
    )
    await trust_repository.link_farmer_market_actor(
        session, farmer.id, market_actor.id
    )
    await trust_repository.link_farmer_social_group(
        session, farmer.id, social_group.id
    )
    return farmer, trust_source, market_actor, social_group


class FakeScoringService:
    async def compute_score(self, session, farmer_id):
        return {"farmer_id": farmer_id, "score": 75}


async def test_start_verification_creates_three_contacted_participants():
    async with db() as Session:
        async with Session() as session:
            farmer, *_ = await arrange(session)
            service = VerificationService()
            verification_session = await service.start_verification(session, farmer.id)
            participants = await service.verification_repository.list_participants_for_session(
                session, verification_session.id
            )
            assert len(participants) == 3
            assert {item.participant_type for item in participants} == {
                "trust_source",
                "market_actor",
                "social_group",
            }
            assert all(item.contacted_at is not None for item in participants)
            assert all(item.responded_at is None for item in participants)
            await session.rollback()


async def test_trust_response_creates_testimonial():
    async with db() as Session:
        async with Session() as session:
            farmer, *_ = await arrange(session)
            service = VerificationService()
            verification_session = await service.start_verification(session, farmer.id)
            participant = next(
                item
                for item in await service.verification_repository.list_participants_for_session(
                    session, verification_session.id
                )
                if item.participant_type == "trust_source"
            )
            await service.submit_response(
                session,
                verification_session.id,
                participant.id,
                {"rating": 3, "comments": "Known farmer", "personal_knowledge_flag": True},
            )
            testimonial = (
                await session.execute(
                    select(signals.Testimonial).where(
                        signals.Testimonial.participant_id == participant.id
                    )
                )
            ).scalar_one()
            assert testimonial.rating == 3
            await session.rollback()


async def test_no_personal_knowledge_creates_no_testimonial_and_stores_summary():
    async with db() as Session:
        async with Session() as session:
            farmer, *_ = await arrange(session)
            service = VerificationService()
            verification_session = await service.start_verification(session, farmer.id)
            participant = next(
                item
                for item in await service.verification_repository.list_participants_for_session(
                    session, verification_session.id
                )
                if item.participant_type == "trust_source"
            )
            await service.submit_response(
                session,
                verification_session.id,
                participant.id,
                {"rating": 3, "personal_knowledge_flag": False},
            )
            assert (
                await session.execute(
                        select(signals.Testimonial).where(
                            signals.Testimonial.participant_id == participant.id
                    )
                )
            ).scalar_one_or_none() is None
            refreshed = await session.get(VerificationParticipant, participant.id)
            assert refreshed.response == "no_personal_knowledge"
            await session.rollback()


async def test_duplicate_response_raises_without_second_signal():
    async with db() as Session:
        async with Session() as session:
            farmer, *_ = await arrange(session)
            service = VerificationService()
            verification_session = await service.start_verification(session, farmer.id)
            participant = next(
                item
                for item in await service.verification_repository.list_participants_for_session(
                    session, verification_session.id
                )
                if item.participant_type == "trust_source"
            )
            payload = {"rating": 3, "personal_knowledge_flag": True}
            await service.submit_response(
                session, verification_session.id, participant.id, payload
            )
            with pytest.raises(ParticipantAlreadyRespondedError):
                await service.submit_response(
                    session, verification_session.id, participant.id, payload
                )
            assert len(
                (
                    await session.execute(
                        select(signals.Testimonial).where(
                            signals.Testimonial.participant_id == participant.id
                        )
                    )
                ).scalars().all()
            ) == 1
            await session.rollback()


async def test_third_response_completes_and_returns_score():
    async with db() as Session:
        async with Session() as session:
            farmer, *_ = await arrange(session)
            service = VerificationService(scoring_service=FakeScoringService())
            verification_session = await service.start_verification(session, farmer.id)
            participants = await service.verification_repository.list_participants_for_session(
                session, verification_session.id
            )
            results = []
            payloads = {
                "trust_source": {"rating": 3, "personal_knowledge_flag": True},
                "market_actor": {"reliability_rating": 4},
                "social_group": {"consecutive_cycles": 6},
            }
            for participant in participants:
                results.append(
                    await service.submit_response(
                        session,
                        verification_session.id,
                        participant.id,
                        payloads[participant.participant_type],
                    )
                )
            assert results[0]["session_status"] == "in_progress"
            assert results[1]["score_result"] is None
            assert results[2]["session_status"] == "completed"
            assert results[2]["score_result"] is not None
            await session.rollback()


async def test_timeout_on_last_participant_completes_session():
    async with db() as Session:
        async with Session() as session:
            farmer, *_ = await arrange(session)
            service = VerificationService(scoring_service=FakeScoringService())
            verification_session = await service.start_verification(session, farmer.id)
            participants = await service.verification_repository.list_participants_for_session(
                session, verification_session.id
            )
            for participant in participants:
                if participant.participant_type == "social_group":
                    continue
                await service.submit_response(
                    session,
                    verification_session.id,
                    participant.id,
                    {"rating": 3, "personal_knowledge_flag": True}
                    if participant.participant_type == "trust_source"
                    else {"reliability_rating": 4},
                )
            social_group_participant = next(
                item
                for item in participants
                if item.participant_type == "social_group"
            )
            result = await service.mark_participant_timeout(
                session, verification_session.id, social_group_participant.id
            )
            assert result["session_status"] == "completed"
            assert result["score_result"] is not None
            await session.rollback()
