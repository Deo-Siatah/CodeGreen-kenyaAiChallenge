"""Integration tests for the scoring role's farmer column boundary.

These tests use settings.TEST_DATABASE_URL_DIRECT through db_target.py. They
refuse pooler hosts and skip only when no throwaway direct target is configured.
"""

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from core.config import settings
from core.database import build_engine

from db_target import TEST_URL, skip_marker

pytestmark = skip_marker()

_URL = TEST_URL or ""


@pytest_asyncio.fixture(scope="module")
async def scoring_engine():
    engine = build_engine(
        _URL,
        scoring_role=settings.DB_SCORING_ROLE,
        pool_size=1,
        max_overflow=0,
        name="TEST_DATABASE_URL_DIRECT",
    )
    try:
        yield engine
    finally:
        await engine.dispose()


async def test_scoring_role_can_read_safe_farmer_view(scoring_engine):
    async with scoring_engine.connect() as connection:
        result = await connection.execute(
            text("SELECT id, full_name, national_id FROM farmers_scoring_safe LIMIT 1")
        )

    assert list(result.keys()) == ["id", "full_name", "national_id"]


async def test_scoring_role_cannot_read_farmer_gender(scoring_engine):
    async with scoring_engine.connect() as connection:
        with pytest.raises(DBAPIError):
            await connection.execute(text("SELECT gender FROM farmers LIMIT 1"))
