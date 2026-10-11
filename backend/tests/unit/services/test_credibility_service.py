import contextlib

import pytest
from sqlalchemy import select
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import _asyncpg_url, _ssl_connect_args
from models.credibility import VerifierCredibility
from models.trust import TrustSource
from services.credibility_service import CredibilityService
from tests.integration.db_target import TEST_URL


@pytest.fixture
def credibility_service():
    return CredibilityService()


async def test_record_loan_outcome_repaid_then_defaulted(credibility_service):
    """record_loan_outcome("repaid") followed by record_loan_outcome("defaulted")
    on the same trust_source_id produces credibility_score matching the
    formula from credibility_repository (already tested in Section 4 — this
    test just confirms the service-level wrapper produces the identical value,
    not re-deriving the formula).
    """
    async with db() as Session:
        async with Session() as s:
            # Create a trust source to test with
            trust_source = TrustSource(full_name="Test Trust Source", category="chief")
            s.add(trust_source)
            await s.flush()
            trust_source_id = trust_source.id

            # First loan outcome: repaid
            credibility1 = await credibility_service.record_loan_outcome(
                session=s, subject_type="trust_source", subject_id=trust_source_id, outcome="repaid"
            )

            # Verify credibility score after repaid
            assert credibility1.subject_type == "trust_source"
            assert credibility1.subject_id == trust_source_id
            assert credibility1.total_endorsements == 1
            assert credibility1.repaid_count == 1
            assert credibility1.defaulted_count == 0
            assert credibility1.credibility_score == 1.0833333333333333  # (1/1) * 1.0 + 0.5 * (1-0)/(1+0+5) = 1.083

            # Second loan outcome: defaulted
            credibility2 = await credibility_service.record_loan_outcome(
                session=s, subject_type="trust_source", subject_id=trust_source_id, outcome="defaulted"
            )

            # Verify credibility score after defaulted
            assert credibility2.subject_type == "trust_source"
            assert credibility2.subject_id == trust_source_id
            assert credibility2.total_endorsements == 2
            assert credibility2.repaid_count == 1
            assert credibility2.defaulted_count == 1
            assert credibility2.credibility_score == 1.0  # (1/2) * 1.0 + 0.5 * (1-1)/(1+1+5) = 1.0

            await s.rollback()


async def test_record_loan_outcome_creates_audit_log(credibility_service):
    """record_loan_outcome also writes an audit log row via audit_service — assert
    both the credibility update and the audit row exist after one call.
    """
    async with db() as Session:
        async with Session() as s:
            # Create a trust source to test with
            trust_source = TrustSource(full_name="Test Trust Source", category="chief")
            s.add(trust_source)
            await s.flush()
            trust_source_id = trust_source.id

            # Record a loan outcome
            credibility = await credibility_service.record_loan_outcome(
                session=s, subject_type="trust_source", subject_id=trust_source_id, outcome="repaid"
            )

            # Verify credibility record exists
            assert credibility.subject_type == "trust_source"
            assert credibility.subject_id == trust_source_id
            assert credibility.total_endorsements == 1
            assert credibility.repaid_count == 1
            assert credibility.defaulted_count == 0
            assert credibility.credibility_score == 1.0833333333333333

            # Verify audit log was created
            from models.audit import AuditLog
            audit_result = await s.execute(
                select(AuditLog).where(
                    AuditLog.entity_type == "verifier_credibility",
                    AuditLog.entity_id == str(trust_source_id),
                    AuditLog.action == "credibility_updated",
                )
            )
            audit_log = audit_result.scalar_one()

            assert audit_log.actor_type == "system"
            assert audit_log.action == "credibility_updated"
            assert audit_log.entity_type == "verifier_credibility"
            assert audit_log.entity_id == trust_source_id
            assert audit_log.details == {"outcome": "repaid"}

            await s.rollback()


async def test_get_or_create_creates_new_if_not_exists(credibility_service):
    """get_or_create should create a new VerifierCredibility if none exists."""
    async with db() as Session:
        async with Session() as s:
            trust_source = TrustSource(full_name="Test Trust Source", category="chief")
            s.add(trust_source)
            await s.flush()
            trust_source_id = trust_source.id

            # Get or create should create a new record
            credibility = await credibility_service.get_or_create(
                session=s, subject_type="trust_source", subject_id=trust_source_id
            )

            assert credibility.subject_type == "trust_source"
            assert credibility.subject_id == trust_source_id
            assert credibility.total_endorsements == 0
            assert credibility.repaid_count == 0
            assert credibility.defaulted_count == 0
            assert credibility.credibility_score == 1.0

            # Query it back to confirm it was saved
            result = await s.execute(
                select(VerifierCredibility).where(
                    VerifierCredibility.subject_type == "trust_source",
                    VerifierCredibility.subject_id == trust_source_id
                )
            )
            retrieved = result.scalar_one()
            assert retrieved == credibility

            await s.rollback()


async def test_get_or_create_returns_existing_if_exists(credibility_service):
    """get_or_create should return existing VerifierCredibility if it exists."""
    async with db() as Session:
        async with Session() as s:
            trust_source = TrustSource(full_name="Test Trust Source", category="chief")
            s.add(trust_source)
            await s.flush()
            trust_source_id = trust_source.id

            # Create a credibility record first
            credibility1 = await credibility_service.get_or_create(
                session=s, subject_type="trust_source", subject_id=trust_source_id
            )

            # Get or create again should return the same record
            credibility2 = await credibility_service.get_or_create(
                session=s, subject_type="trust_source", subject_id=trust_source_id
            )

            assert credibility1.id == credibility2.id
            assert credibility1.subject_type == credibility2.subject_type
            assert credibility1.subject_id == credibility2.subject_id

            await s.rollback()


@contextlib.asynccontextmanager
async def db():
    """A session factory on a throwaway engine. NullPool, so no shared state."""
    _URL = TEST_URL or ""

    engine = create_async_engine(
        _asyncpg_url(_URL, "TEST_DATABASE_URL_DIRECT"),
        poolclass=pool.NullPool,
        connect_args=_ssl_connect_args(_URL, "TEST_DATABASE_URL_DIRECT"),
    )
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()