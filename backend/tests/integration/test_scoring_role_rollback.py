r"""
Integration tests: does the scoring role survive pool reuse?

These cover the failure that a connect-time-only SET ROLE cannot defend
against. The asyncpg adapter opens an implicit transaction for any cursor
execute, so an uncommitted `SET ROLE` is part of a transaction that SQLAlchemy
rolls back when the connection returns to the pool. A scoring session that only
reads never commits, so a connect-only listener would hand back the scoring role
on the first checkout and the login role on every one after it - and the login
role can read farmers.gender.

GATED ON TEST_DATABASE_URL_DIRECT
---------------------------------
These tests CREATE A ROLE on whatever database they are pointed at and drop it
again afterwards. They deliberately do NOT read DATABASE_URL_DIRECT, so that a
plain `pytest` run against a developer's real configuration cannot create
anything on main.

The setting is read from settings.TEST_DATABASE_URL_DIRECT, and the rules live
in db_target.py: skip when it is unset, refuse to run against a pooler host or
against the same host as DATABASE_URL_DIRECT.

    # .env - a throwaway Neon BRANCH's DIRECT (non-pooler) endpoint
    TEST_DATABASE_URL_DIRECT=postgresql://...
    cd backend
    uv run pytest tests/integration/test_scoring_role_rollback.py -v

The engine under test is built with pool_size=1, max_overflow=0 so that every
checkout is guaranteed to be a reuse of the same single connection, which is
what makes the rollback visible.
"""

import pytest
import pytest_asyncio
from sqlalchemy import text

from core.database import build_engine

from db_target import TEST_URL, skip_marker

TEST_ROLE = "hifadhi_test_scoring"

_CURRENT_USER = text("SELECT current_user")

pytestmark = skip_marker()

_URL = TEST_URL or ""


@pytest_asyncio.fixture(scope="module")
async def admin_engine():
    """A plain engine, with no role forced on it, for DDL.

    The role has to be created and granted before any engine tries to SET ROLE
    to it, and the test engine cannot be used for that - it would already be
    trying to be a role that does not exist yet.
    """
    engine = build_engine(_URL, pool_size=1, max_overflow=0, name="TEST_DATABASE_URL_DIRECT")
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def test_role(admin_engine):
    """Create TEST_ROLE, grant it to the login role, and always drop it after.

    Teardown runs even when a test fails or the session is interrupted, because
    it is in a finally block. CREATE ROLE is transactional in Postgres, but a
    rollback would not be enough here: the GRANT is what the test relies on, and
    leaving either behind would be a change to a database this suite was only
    lent.

    The pre-clean is DROP ROLE IF EXISTS rather than REVOKE + DROP. There is no
    `REVOKE IF EXISTS` in Postgres - REVOKE has no IF EXISTS clause, so that
    spelling is a syntax error and the fixture never got as far as creating the
    role. It is also unnecessary: dropping a role deletes the privilege entries
    that mention it, so a leftover GRANT goes with the DROP.
    """
    async with admin_engine.begin() as conn:
        login_role = (await conn.execute(_CURRENT_USER)).scalar_one()
        # A previous run that was killed before teardown could have left this
        # behind; clear it so CREATE ROLE is not blocked.
        await conn.execute(text(f'DROP ROLE IF EXISTS "{TEST_ROLE}"'))
        await conn.execute(text(f'CREATE ROLE "{TEST_ROLE}" NOLOGIN'))
        await conn.execute(text(f'GRANT "{TEST_ROLE}" TO "{login_role}"'))

    try:
        yield TEST_ROLE
    finally:
        async with admin_engine.begin() as conn:
            await conn.execute(text(f'DROP ROLE IF EXISTS "{TEST_ROLE}"'))


@pytest_asyncio.fixture
async def scoring_engine(admin_engine, test_role):
    """One pooled connection, forced to TEST_ROLE, reused by every checkout."""
    engine = build_engine(
        _URL,
        scoring_role=test_role,
        pool_size=1,
        max_overflow=0,
        name="TEST_DATABASE_URL_DIRECT",
    )
    try:
        yield engine
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# 6. Role persists across plain pool reuse
# ---------------------------------------------------------------------------


async def test_role_survives_pool_reuse(scoring_engine, test_role):
    """Twenty checkout/return cycles, all on the same one pooled connection."""
    for attempt in range(20):
        async with scoring_engine.connect() as connection:
            current_user = (await connection.execute(_CURRENT_USER)).scalar_one()

        assert current_user == test_role, (
            f"checkout {attempt} came back as {current_user!r}, expected "
            f"{test_role!r}"
        )


# ---------------------------------------------------------------------------
# 7. The rollback path - the test that would have caught the bug
# ---------------------------------------------------------------------------


async def test_role_survives_read_only_session_that_never_commits(
    scoring_engine, test_role
):
    """Scoring sessions mostly read, and reading never commits.

    On return to the pool SQLAlchemy rolls the connection back, and a
    transaction-scoped SET ROLE is reverted by that rollback. Without the
    explicit commit in the connect listener this returns the login role from
    the second checkout onwards.
    """
    for attempt in range(10):
        async with scoring_engine.connect() as connection:
            # SELECT only. No commit, no explicit transaction.
            current_user = (await connection.execute(_CURRENT_USER)).scalar_one()
            assert await connection.execute(text("SELECT 1")) is not None
            if attempt == 0:
                first = current_user
        # Connection returned to the pool here, and rolled back on the way.

    assert first == test_role
    assert current_user == test_role, (
        "a read-only session that never committed reverted the role, so the "
        "scoring path would be reading with the login role"
    )


async def test_role_survives_explicit_rollback(scoring_engine, test_role):
    """An explicit ROLLBACK is the same hazard, done on purpose.

    connection.rollback() rather than begin() + Transaction.rollback(): the
    execute() above has already autobegun, so an explicit begin() would raise.
    """
    for _ in range(5):
        connection = await scoring_engine.connect()
        try:
            current_user = (await connection.execute(_CURRENT_USER)).scalar_one()
            await connection.rollback()
        finally:
            await connection.close()

        assert current_user == test_role


# ---------------------------------------------------------------------------
# 8. The commit path
# ---------------------------------------------------------------------------


async def test_role_survives_session_that_commits(scoring_engine, test_role):
    """connection.commit() rather than begin() + Transaction.commit().

    The execute() above has already autobegun, so an explicit begin() would
    raise InvalidRequestError. Committing the connection is the same operation.
    """
    for _ in range(5):
        async with scoring_engine.connect() as connection:
            current_user = (await connection.execute(_CURRENT_USER)).scalar_one()
            await connection.commit()

        assert current_user == test_role


# ---------------------------------------------------------------------------
# 9. Drift
# ---------------------------------------------------------------------------


async def test_drift_is_caught_rather_than_served(scoring_engine, test_role):
    """A connection whose role was reset must never reach a caller.

    Something outside the listeners can still run RESET ROLE on a pooled
    connection. The checkout listener re-reads current_user and raises
    DisconnectionError, which makes the pool invalidate that connection and
    retry, so what comes back is either correct or an error - never the login
    role.
    """
    # Drift it deliberately.
    async with scoring_engine.connect() as connection:
        await connection.execute(text("RESET ROLE"))
        drifted = (await connection.execute(_CURRENT_USER)).scalar_one()
    assert drifted != test_role, "RESET ROLE did not actually take effect"

    # Now the next checkout must not hand that role back.
    async with scoring_engine.connect() as connection:
        recovered = (await connection.execute(_CURRENT_USER)).scalar_one()

    assert recovered == test_role, (
        f"a drifted connection was handed back running as {recovered!r}"
    )


async def test_scoring_session_never_reports_the_login_role(scoring_engine, test_role):
    """Belt and braces across a mixed workload of reads, commits and rollbacks.

    Whatever the transaction does, current_user must be TEST_ROLE on every
    checkout.
    """
    for attempt in range(15):
        async with scoring_engine.connect() as connection:
            if attempt % 3 == 0:
                pass  # read only, never commits
            elif attempt % 3 == 1:
                transaction = await connection.begin()
                await transaction.commit()
            else:
                transaction = await connection.begin()
                await transaction.rollback()

            current_user = (await connection.execute(_CURRENT_USER)).scalar_one()

        assert current_user == test_role, f"attempt {attempt} ran as {current_user!r}"


# Note on teardown: the `test_role` fixture drops the role in a finally block
# once the module finishes, so the database is left as it was found. That is
# also why it opens with DROP ROLE IF EXISTS - if a run is killed before
# teardown, the next run clears the leftover rather than failing on it. The
# residue is a role with no grants and no login, not a modified schema.
