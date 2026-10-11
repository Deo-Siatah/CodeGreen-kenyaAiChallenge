import uuid
from datetime import datetime

import pytest
from sqlalchemy import select

from models.audit import AuditLog
from services.audit_service import AuditService


@pytest.fixture
def audit_service():
    return AuditService()


async def test_write_log_persists_and_flushes_without_commit(audit_service):
    """write_log persists a row with the given fields; querying it back
    immediately (same uncommitted transaction) returns it, proving flush()
    worked without needing a commit.
    """
    async with db() as Session:
        async with Session() as s:
            actor_id = uuid.uuid4()
            entity_id = uuid.uuid4()
            details = {"key": "value"}

            log_entry = await audit_service.write_log(
                session=s,
                actor_type="user",
                actor_id=actor_id,
                action="login",
                entity_type="session",
                entity_id=entity_id,
                details=details,
            )

            # Verify the returned object has the correct values
            assert log_entry.actor_type == "user"
            assert log_entry.actor_id == actor_id
            assert log_entry.action == "login"
            assert log_entry.entity_type == "session"
            assert log_entry.entity_id == entity_id
            assert log_entry.details == details
            assert log_entry.created_at is not None

            # Query it back from the database in the same session
            result = await s.execute(
                select(AuditLog).where(AuditLog.id == log_entry.id)
            )
            retrieved = result.scalar_one()
            assert retrieved == log_entry

            # Rollback to clean up
            await s.rollback()


async def test_write_log_with_no_details(audit_service):
    """Test that None details is handled correctly."""
    async with db() as Session:
        async with Session() as s:
            entity_id = uuid.uuid4()
            actor_id = uuid.uuid4()  # UUID for actor_id

            log_entry = await audit_service.write_log(
                session=s,
                actor_type="system",
                actor_id=actor_id,
                action="test_action",
                entity_type="test_entity",
                entity_id=entity_id,
                details=None,  # This should work fine
            )

            assert log_entry.details is None
            await s.rollback()


async def test_write_log_with_empty_dict_details(audit_service):
    """Test that empty dict details is handled correctly."""
    async with db() as Session:
        async with Session() as s:
            entity_id = uuid.uuid4()
            actor_id = uuid.uuid4()  # UUID for actor_id

            log_entry = await audit_service.write_log(
                session=s,
                actor_type="system",
                actor_id=actor_id,
                action="test_action",
                entity_type="test_entity",
                entity_id=entity_id,
                details={},  # This should work fine
            )

            assert log_entry.details == {}
            await s.rollback()


# Database connection setup for tests
import contextlib
import sys
from pathlib import Path

# Add the integration tests directory to the path to import db_target
sys.path.append(str(Path(__file__).parent.parent.parent / "integration"))

from core.database import _asyncpg_url, _ssl_connect_args
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import pool


@contextlib.asynccontextmanager
async def db():
    """A session factory on a throwaway engine. NullPool, so no shared state."""
    from db_target import TEST_URL

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