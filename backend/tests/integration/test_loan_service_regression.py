r"""
Regression tests for loan service fixes.

Tests for the MissingGreenlet crash fix and improved error handling.
These tests run against a real database session and verify:

1. The eager_defaults=True fix prevents MissingGreenlet crashes
2. Proper exception handling for loan operations
3. All loan columns can be read after operations without triggering lazy reloads

These tests SKIP, loudly and with a reason, when there is no database to talk to,
so `uv run pytest` stays green offline. Run them with a populated `.env`:

    cd backend
    uv run pytest tests/integration/test_loan_service_regression.py -v

PREREQUISITES
-------------
  * a `.env` with TEST_DATABASE_URL_DIRECT pointing at a reachable Postgres
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from core.config import settings
    from core.database import (
        dispose_engines,
        engine_app,
        get_db_session,
    )
    from models.farmer import Farmer
    from models.loan import Loan
    from models.scoring import ScoreProfile
    from services.loan_service import (
        LoanService,
        LoanNotFoundError,
        InvalidLoanStateError,
    )
except Exception as exc:  # missing .env, unset required setting, bad driver
    pytest.skip(
        f"core.database is not importable ({type(exc).__name__}: {exc}). "
        "These tests need a populated .env.",
        allow_module_level=True,
    )

# Check if TEST_DATABASE_URL_DIRECT is set
if not hasattr(settings, 'TEST_DATABASE_URL_DIRECT') or not settings.TEST_DATABASE_URL_DIRECT:
    pytest.skip(
        "TEST_DATABASE_URL_DIRECT is not set. These tests need a direct database connection.",
        allow_module_level=True,
    )


@asynccontextmanager
async def open_session(dependency):
    """Drive a FastAPI dependency generator the way the framework does.

    Advances to the yielded session, then runs the generator's teardown on the
    way out. The teardown has to happen *after* the test body finishes, which
    is why this is a context manager rather than a helper returning a session.
    """
    generator = dependency()
    try:
        yield await generator.__anext__()
    finally:
        await generator.aclose()


@pytest_asyncio.fixture(scope="module", autouse=True)
async def _require_a_live_database():
    """Skip the module if TEST_DATABASE_URL_DIRECT does not actually connect."""
    try:
        async with engine_app.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(
            f"No reachable Postgres at TEST_DATABASE_URL_DIRECT "
            f"({type(exc).__name__}). Set it in .env to run these tests."
        )
    yield
    await dispose_engines()


@pytest_asyncio.fixture
async def db_session():
    """Get a database session for testing."""
    async with open_session(get_db_session) as session:
        yield session


@pytest_asyncio.fixture
async def farmer(db_session: AsyncSession):
    """Create a farmer for testing."""
    farmer = Farmer(
        name="Test Farmer",
        phone_number="254712345678",
        email="test@example.com",
        location="Test Location",
        gender="male",
        date_of_birth=datetime(1990, 1, 1),
    )
    db_session.add(farmer)
    await db_session.flush()
    yield farmer
    # Cleanup
    await db_session.delete(farmer)
    await db_session.commit()


@pytest_asyncio.fixture
async def score_profile(db_session: AsyncSession, farmer):
    """Create a score profile for testing."""
    score_profile = ScoreProfile(
        farmer_id=farmer.id,
        character_score=0.8,
        capacity_score=0.7,
        combined_score=0.75,
        recommended_amount=10000.0,
        score_updated_at=datetime.now(timezone.utc),
    )
    db_session.add(score_profile)
    await db_session.flush()
    yield score_profile
    # Cleanup
    await db_session.delete(score_profile)
    await db_session.commit()


@pytest_asyncio.fixture
async def loan(db_session: AsyncSession, farmer, score_profile):
    """Create a loan for testing."""
    loan = Loan(
        farmer_id=farmer.id,
        amount=5000.0,
        purpose="Test loan",
        status="pending_disbursement",
        applied_at=datetime.now(timezone.utc),
        score_profile_id=score_profile.id,
    )
    db_session.add(loan)
    await db_session.flush()
    yield loan
    # Cleanup
    await db_session.delete(loan)
    await db_session.commit()


async def test_mark_disburred_reads_all_columns_without_missing_greenlet(db_session: AsyncSession, farmer, score_profile):
    """Test that mark_disbursed can read all columns without triggering MissingGreenlet."""
    # Create a loan
    loan = Loan(
        farmer_id=farmer.id,
        amount=5000.0,
        purpose="Test loan",
        status="pending_disbursement",
        applied_at=datetime.now(timezone.utc),
        score_profile_id=score_profile.id,
    )
    db_session.add(loan)
    await db_session.flush()
    
    # Mark it as disbursed
    loan_service = LoanService()
    result = await loan_service.mark_disbursed(db_session, loan.id)
    await db_session.commit()
    
    # Read EVERY column of the returned Loan (this used to trigger MissingGreenlet)
    all_columns = {}
    for column in Loan.__table__.columns:
        all_columns[column.name] = getattr(result, column.name)
    
    # Verify all expected columns are present and have reasonable values
    assert all_columns['id'] == loan.id
    assert all_columns['farmer_id'] == farmer.id
    assert all_columns['amount'] == 5000.0
    assert all_columns['status'] == 'disbursed'
    assert all_columns['disbursed_at'] is not None
    assert all_columns['updated_at'] is not None  # This should work without MissingGreenlet
    assert all_columns['created_at'] is not None


async def test_resolve_loan_repaid_reads_all_columns_without_missing_greenlet(db_session: AsyncSession, farmer, score_profile):
    """Test that resolve_loan (repaid) can read all columns without triggering MissingGreenlet."""
    # Create a disbursed loan
    loan = Loan(
        farmer_id=farmer.id,
        amount=5000.0,
        purpose="Test loan",
        status="disbursed",
        disbursed_at=datetime.now(timezone.utc),
        applied_at=datetime.now(timezone.utc),
        score_profile_id=score_profile.id,
    )
    db_session.add(loan)
    await db_session.flush()
    
    # Resolve it as repaid
    loan_service = LoanService()
    result = await loan_service.resolve_loan(db_session, loan.id, "repaid")
    await db_session.commit()
    
    # Read EVERY column of the returned Loan (this used to trigger MissingGreenlet)
    all_columns = {}
    for column in Loan.__table__.columns:
        all_columns[column.name] = getattr(result, column.name)
    
    # Verify all expected columns are present and have reasonable values
    assert all_columns['id'] == loan.id
    assert all_columns['farmer_id'] == farmer.id
    assert all_columns['amount'] == 5000.0
    assert all_columns['status'] == 'repaid'
    assert all_columns['repaid_at'] is not None
    assert all_columns['updated_at'] is not None  # This should work without MissingGreenlet
    assert all_columns['created_at'] is not None


async def test_resolve_loan_defaulted_reads_all_columns_without_missing_greenlet(db_session: AsyncSession, farmer, score_profile):
    """Test that resolve_loan (defaulted) can read all columns without triggering MissingGreenlet."""
    # Create a disbursed loan
    loan = Loan(
        farmer_id=farmer.id,
        amount=5000.0,
        purpose="Test loan",
        status="disbursed",
        disbursed_at=datetime.now(timezone.utc),
        applied_at=datetime.now(timezone.utc),
        score_profile_id=score_profile.id,
    )
    db_session.add(loan)
    await db_session.flush()
    
    # Resolve it as defaulted
    loan_service = LoanService()
    result = await loan_service.resolve_loan(db_session, loan.id, "defaulted")
    await db_session.commit()
    
    # Read EVERY column of the returned Loan (this used to trigger MissingGreenlet)
    all_columns = {}
    for column in Loan.__table__.columns:
        all_columns[column.name] = getattr(result, column.name)
    
    # Verify all expected columns are present and have reasonable values
    assert all_columns['id'] == loan.id
    assert all_columns['farmer_id'] == farmer.id
    assert all_columns['amount'] == 5000.0
    assert all_columns['status'] == 'defaulted'
    assert all_columns['defaulted_at'] is not None
    assert all_columns['updated_at'] is not None  # This should work without MissingGreenlet
    assert all_columns['created_at'] is not None


async def test_mark_disbursed_on_nonexistent_loan_raises_loan_not_found(db_session: AsyncSession):
    """Test that mark_disbursed raises LoanNotFoundError for nonexistent loan."""
    loan_service = LoanService()
    
    with pytest.raises(LoanNotFoundError) as exc_info:
        await loan_service.mark_disbursed(db_session, uuid4())
    
    assert "not found" in str(exc_info.value)


async def test_mark_disbursed_on_already_disbursed_loan_raises_invalid_loan_state(db_session: AsyncSession, farmer, score_profile):
    """Test that mark_disbursed raises InvalidLoanStateError for already disbursed loan."""
    # Create a disbursed loan
    loan = Loan(
        farmer_id=farmer.id,
        amount=5000.0,
        purpose="Test loan",
        status="disbursed",
        disbursed_at=datetime.now(timezone.utc),
        applied_at=datetime.now(timezone.utc),
        score_profile_id=score_profile.id,
    )
    db_session.add(loan)
    await db_session.flush()
    
    loan_service = LoanService()
    
    with pytest.raises(InvalidLoanStateError) as exc_info:
        await loan_service.mark_disbursed(db_session, loan.id)
    
    assert "not pending disbursement" in str(exc_info.value)


async def test_resolve_loan_on_never_disbursed_loan_raises_invalid_loan_state(db_session: AsyncSession, farmer, score_profile):
    """Test that resolve_loan raises InvalidLoanStateError for loan that was never disbursed."""
    # Create a pending loan
    loan = Loan(
        farmer_id=farmer.id,
        amount=5000.0,
        purpose="Test loan",
        status="pending_disbursement",
        applied_at=datetime.now(timezone.utc),
        score_profile_id=score_profile.id,
    )
    db_session.add(loan)
    await db_session.flush()
    
    loan_service = LoanService()
    
    with pytest.raises(InvalidLoanStateError) as exc_info:
        await loan_service.resolve_loan(db_session, loan.id, "repaid")
    
    assert "not disbursed" in str(exc_info.value)