r"""
Integration tests: the two session dependencies against a real Postgres.

These are the tests that cannot be faked. `get_db_session()` and
`get_scoring_session()` are the seam where the scoring role is supposed to
become a property of the connection rather than a convention in the code, and
the only way to observe that is to ask the server who it thinks it is. A mocked
driver would return whatever the mock was told to return and prove nothing.

They SKIP, loudly and with a reason, when there is no database to talk to, so
`uv run pytest` stays green offline. Run them with a populated `.env`:

    cd backend
    uv run pytest tests/integration/test_database_sessions.py -v

PREREQUISITES
-------------
  * a `.env` with DATABASE_URL_POOLED pointing at a reachable Postgres, and
  * the scoring role existing and granted to the login role:
        CREATE ROLE app_scoring NOLOGIN;
        GRANT app_scoring TO <the login role in DATABASE_URL_POOLED>;
    Without the GRANT every scoring connection is refused and these tests
    fail. That is the intended fail-closed behaviour, not a broken test.
"""

from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from core.config import settings
    from core.database import (
        dispose_engines,
        engine_app,
        engine_scoring,
        get_db_session,
        get_scoring_session,
    )
except Exception as exc:  # missing .env, unset required setting, bad driver
    pytest.skip(
        f"core.database is not importable ({type(exc).__name__}: {exc}). "
        "These tests need a populated .env.",
        allow_module_level=True,
    )

# The two things a session has to be able to tell us: that it executes SQL, and
# that Postgres reports the role we expect for it.
_SELECT_ONE = text("SELECT 1")
_CURRENT_USER = text("SELECT current_user")
# missing_ok -> NULL instead of an error if `role` was never set on the session.
_CURRENT_ROLE_SETTING = text("SELECT current_setting('role', true)")


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
    """Skip the module if DATABASE_URL_POOLED does not actually connect."""
    try:
        async with engine_app.connect() as connection:
            await connection.execute(_SELECT_ONE)
    except Exception as exc:
        pytest.skip(
            f"No reachable Postgres at DATABASE_URL_POOLED "
            f"({type(exc).__name__}). Set it in .env to run these tests."
        )
    yield
    await dispose_engines()


# ---------------------------------------------------------------------------
# 1. get_db_session
# ---------------------------------------------------------------------------


async def test_get_db_session_yields_a_session_that_runs_select_one():
    async with open_session(get_db_session) as session:
        result = await session.execute(_SELECT_ONE)

        assert result.scalar_one() == 1


async def test_get_db_session_yields_a_live_async_session():
    """Catches the dependency handing back a detached session, or one that was
    already closed by its own teardown."""
    async with open_session(get_db_session) as session:
        assert isinstance(session, AsyncSession)
        assert session.is_active
        # Still usable for a second statement, i.e. not detached.
        assert (await session.execute(_CURRENT_USER)).scalar_one()


async def test_get_db_session_is_bound_to_the_app_engine():
    """The general dependency must not be able to serve scoring traffic."""
    async with open_session(get_db_session) as session:
        # get_bind() hands back the sync facade of the engine it is bound to.
        assert session.get_bind() is engine_app.sync_engine
        assert session.get_bind() is not engine_scoring.sync_engine


async def test_get_db_session_returns_the_connection_to_the_pool():
    """A request-scoped dependency that does not close leaks one pooled
    connection per request until the pool is exhausted."""
    checkouts: list = []
    checkins: list = []
    # event.listen returns None; the listener function itself is the handle
    # event.remove needs, so both are kept.
    on_checkout = lambda *_: checkouts.append(1)  # noqa: E731
    on_checkin = lambda *_: checkins.append(1)  # noqa: E731
    event.listen(engine_app.sync_engine, "checkout", on_checkout)
    event.listen(engine_app.sync_engine, "checkin", on_checkin)
    try:
        before = len(checkins)
        async with open_session(get_db_session) as session:
            await session.execute(_SELECT_ONE)

        assert checkouts, "the session never checked a connection out"
        assert len(checkins) > before, (
            "the dependency exited without returning its connection to the pool"
        )
    finally:
        event.remove(engine_app.sync_engine, "checkout", on_checkout)
        event.remove(engine_app.sync_engine, "checkin", on_checkin)


# ---------------------------------------------------------------------------
# 2. get_scoring_session
# ---------------------------------------------------------------------------


async def test_scoring_session_runs_as_the_scoring_role():
    """The core assertion: the role is applied by the server, not by us."""
    async with open_session(get_scoring_session) as session:
        role = (await session.execute(_CURRENT_ROLE_SETTING)).scalar_one()

    assert role == settings.DB_SCORING_ROLE, (
        f"expected the session to run as {settings.DB_SCORING_ROLE!r} but "
        f"current_setting('role') returned {role!r}. Either the pooler is "
        "dropping the `role` startup parameter, or the GRANT is missing."
    )


async def test_scoring_session_current_user_is_the_scoring_role():
    """current_user is the security-relevant view: grants are evaluated against
    it, and unlike a session-level SET ROLE it cannot be re-pointed later."""
    async with open_session(get_scoring_session) as session:
        current_user = (await session.execute(_CURRENT_USER)).scalar_one()

    assert current_user == settings.DB_SCORING_ROLE


async def test_scoring_session_role_differs_from_the_app_session_role():
    """The 'not the default connection role' half.

    Asserting app_scoring on its own would still pass if both engines somehow
    ran as the scoring role. The two sessions have to disagree, which is what
    makes the separation mean anything.
    """
    async with open_session(get_scoring_session) as scoring_session:
        scoring_role = (
            await scoring_session.execute(_CURRENT_ROLE_SETTING)
        ).scalar_one()

    async with open_session(get_db_session) as app_session:
        app_role = (await app_session.execute(_CURRENT_ROLE_SETTING)).scalar_one()

    assert app_role != scoring_role
    assert app_role != settings.DB_SCORING_ROLE, (
        "the general session is also running as the scoring role, so the "
        "separation between the two engines is not actually in effect"
    )


async def test_scoring_session_is_bound_to_the_scoring_engine():
    async with open_session(get_scoring_session) as session:
        assert session.get_bind() is engine_scoring.sync_engine
        assert session.get_bind() is not engine_app.sync_engine


async def test_scoring_session_runs_select_one():
    async with open_session(get_scoring_session) as session:
        assert (await session.execute(_SELECT_ONE)).scalar_one() == 1


async def test_scoring_session_teardown_closes_the_transaction():
    """On an exception the dependency rolls back and closes, so a failed
    request does not leave an open transaction pinned to a pooled connection."""
    generator = get_scoring_session()
    session = await generator.__anext__()
    try:
        async with session.begin():
            await session.execute(_SELECT_ONE)
            raise RuntimeError("handler blew up")
    except RuntimeError:
        pass
    finally:
        await generator.aclose()

    assert not session.in_transaction()


# ---------------------------------------------------------------------------
# The property the whole split exists for.
#
# This one needs the REVOKE SELECT ON farmers.gender FROM app_scoring migration
# from Section 5, so it is expected to fail until then. It is marked xfail
# non-strict on purpose: when the migration lands it will XPASS, which is good
# news, and the marker should then be deleted. A strict marker would turn that
# XPASS into a suite failure and punish the exact change we want.
# --------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="needs the REVOKE SELECT ON farmers.gender FROM app_scoring migration",
    strict=False,
)
async def test_farmer_gender_not_readable_by_scoring_role():
    """The scoring role must be unable to read the protected column."""
    async with open_session(get_scoring_session) as session:
        await session.execute(text("SELECT gender FROM farmers"))
