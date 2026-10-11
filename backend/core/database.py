"""Async Postgres access for the API.

There are two engines, and the difference between them is a Postgres ROLE
rather than a credential:

  engine_app      General purpose. Used by route handlers via get_db_session().
  engine_scoring  Connects directly (not via the pooler) and has every
                  connection run as settings.DB_SCORING_ROLE. Because the
                  role's grants are the enforcement boundary, the scoring path
                  physically cannot SELECT farmers.gender - it is not a
                  convention this codebase has to remember, it is a property of
                  the role. Used only via get_scoring_session().

Nothing in this file grants or revokes anything. The role setup, including
REVOKE SELECT ON farmers.gender FROM app_scoring, is a migration concern.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any, Callable, NamedTuple

from sqlalchemy import event, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError, DisconnectionError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings

logger = logging.getLogger(__name__)

# The libpq query parameters that appear on the Neon URLs in .env. asyncpg's
# connect() has no **kwargs, and SQLAlchemy forwards URL query params straight
# into connect() as keywords, so leaving these in place raises
# "TypeError: connect() got an unexpected keyword argument" on the first
# connection - i.e. at first request, not at import. Strip them here.
# `channel_binding` has no asyncpg equivalent at all and is simply dropped;
# `sslmode` is re-supplied below as connect_args["ssl"], which asyncpg accepts
# as a libpq mode string and maps to identical semantics.
_LIBPQ_ONLY_PARAMS = ("sslmode", "channel_binding", "sslnegotiation")


def _parse_url(raw_url: str, name: str = "Postgres URL") -> URL:
    """Parse and validate a libpq-style Postgres URL, query string intact.

    The single point where a bad URL becomes a readable error. Everything else
    that needs the URL goes through here, so no caller can reach SQLAlchemy's
    ArgumentError by parsing on its own.

    `name` is the setting the URL came from, so the error points at the right
    variable instead of always blaming DATABASE_URL_POOLED.
    """
    try:
        url = make_url(raw_url)
    except ArgumentError as exc:
        raise ValueError(
            f"{name} is not a parseable Postgres URL: {exc}. Expected something "
            "like 'postgresql://user:pass@host:5432/dbname'."
        ) from exc

    if not url.drivername.startswith("postgres"):
        raise ValueError(f"{name} must be a Postgres URL, got {url.drivername!r}")

    return url


def _asyncpg_url(raw_url: str, name: str = "Postgres URL") -> URL:
    """Normalise a libpq-style Postgres URL for the asyncpg dialect."""
    url = _parse_url(raw_url, name)
    query = {k: v for k, v in url.query.items() if k not in _LIBPQ_ONLY_PARAMS}

    return url.set(drivername="postgresql+asyncpg", query=query)


def _ssl_connect_args(raw_url: str, name: str = "Postgres URL") -> dict[str, str]:
    """Carry `sslmode` from the URL across to asyncpg's `ssl` parameter."""
    sslmode = _parse_url(raw_url, name).query.get("sslmode")
    return {"ssl": sslmode} if sslmode else {}


def _quote_ident(name: str) -> str:
    """Quote a Postgres identifier. DB_SCORING_ROLE is interpolated into a
    SET ROLE statement, so it is quoted rather than trusted."""
    return '"' + name.replace('"', '""') + '"'


class _RoleListeners(NamedTuple):
    """The listeners `_apply_role_on_connect` installed, so tests can drive
    them without reaching into SQLAlchemy's dispatch internals."""

    connect: Callable
    checkout: Callable


def _apply_role_on_connect(engine: AsyncEngine, role: str) -> _RoleListeners:
    """Make every connection on `engine` run as `role`, and keep it that way.

    The role has to be set with a statement. Sending it as a startup-message
    parameter instead - connect_args={"server_settings": {"role": ...}}, which
    looks like the tidier option - does not work: PostgreSQL ignores `role` in
    the startup packet, on a direct connection as well as through a pooler.
    The connection succeeds and quietly runs as the login role instead, which
    is the worst possible failure mode for this boundary.

    Two listeners, because one is not enough:

    connect  SET ROLE, then commit it. The commit is essential. The asyncpg
             adapter opens an implicit transaction for any cursor execute
             (AsyncAdapt_asyncpg_cursor._prepare_and_execute calls
             _start_transaction), so an uncommitted SET ROLE is part of a
             transaction that SQLAlchemy rolls back when the connection returns
             to the pool. A scoring session that only ever reads never commits,
             so without this the first checkout would run as the scoring role
             and every one after it would run as the login role - which can
             read farmers.gender. commit() is a no-op when no transaction is
             open, so it is always safe to call.

    checkout Re-assert the role by asking the server who it is, rather than
             re-issuing SET ROLE. Both are cheap, but re-issuing SET ROLE would
             mask drift: it would paper over a role that had been reset by
             something else, and we would never learn that the boundary had
             been breached. Reading current_user and raising
             DisconnectionError on a mismatch makes the pool discard that
             connection and retry with a fresh one
             (Pool._checkout catches DisconnectionError, invalidates, and
             retries), so a drifted connection is never handed to a caller and
             drift cannot go unnoticed.
    """
    quoted = _quote_ident(role)

    def _set_role(dbapi_connection, connection_record):  # noqa: ARG001
        with dbapi_connection.cursor() as cursor:
            cursor.execute(f"SET ROLE {quoted}")
        # Outside the cursor's implicit transaction, so a pool rollback on
        # return cannot revert the role.
        dbapi_connection.commit()

    def _assert_role(dbapi_connection, connection_record, connection_proxy):  # noqa: ARG001
        # Three parameters, not two: PoolEvents.checkout is dispatched as
        # (dbapi_connection, connection_record, connection_proxy).
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SELECT current_user")
            row = cursor.fetchone()
        # Leaving a read-only transaction open here would be picked up by the
        # session that checks the connection out, so close it. COMMIT does not
        # affect the session-level role.
        dbapi_connection.commit()

        actual = row[0] if row else None
        if actual != role:
            raise DisconnectionError(
                f"scoring connection is running as {actual!r}, expected "
                f"{role!r}. Discarding it rather than handing back a "
                "connection that can read data this role must not see."
            )

    event.listen(engine.sync_engine, "connect", _set_role)
    event.listen(engine.sync_engine, "checkout", _assert_role)
    return _RoleListeners(_set_role, _assert_role)


def build_engine(
    url: str,
    *,
    scoring_role: str | None = None,
    pool_size: int | None = None,
    max_overflow: int | None = None,
    name: str = "Postgres URL",
) -> AsyncEngine:
    """Construct an asyncpg engine for `url`.

    Pass `scoring_role` to have every connection arrive already running as
    that role, and keep arriving that way. `pool_size` / `max_overflow` are
    forwarded to create_async_engine only when given, so leaving them None keeps
    SQLAlchemy's defaults (5 + 10) rather than pinning them.

    Exists as a function rather than only as two module-level engines so a bad
    URL can be turned into a clear error at a point the caller chooses
    (including in tests), rather than only at import time.
    """
    # Validate before anything else touches the URL, so an unparseable or
    # wrong-dialect value always surfaces as the readable ValueError above.
    _parse_url(url, name)

    engine_kwargs: dict[str, Any] = {
        "pool_pre_ping": True,
        "connect_args": _ssl_connect_args(url, name),
    }
    if pool_size is not None:
        engine_kwargs["pool_size"] = pool_size
    if max_overflow is not None:
        engine_kwargs["max_overflow"] = max_overflow

    # pool_pre_ping costs one round trip per checkout but catches connections
    # the pooler or the provider dropped while idle, which is routine on a
    # pooled URL.
    engine = create_async_engine(_asyncpg_url(url, name), **engine_kwargs)

    if scoring_role is not None:
        _apply_role_on_connect(engine, scoring_role)

    return engine


_APP_URL = settings.DATABASE_URL_POOLED

# WHY THE SCORING ENGINE IS NOT POOLED
# ------------------------------------
# DATABASE_URL_POOLED goes through a transaction-mode pooler, and that pooler
# does not reset session state when it hands a server connection to the next
# client. Measured against this project's own .env: a GUC set by one client is
# still set for the next client on the pooled URL, and is correctly gone on the
# direct URL.
#
# That makes SET ROLE over the pooled URL unsafe. A connection left running as
# app_scoring would be handed to a later, unrelated request, and a scoring
# connection could equally be handed a backend still carrying some other
# client's role. The role boundary would be a coin flip rather than a
# guarantee - the scoring path would sometimes be able to read farmers.gender.
#
# The direct URL gives each pooled connection its own server connection, so
# SET ROLE is stable for that connection's lifetime and cannot leak sideways.
# The cost is that scoring connections are not multiplexed through the
# pooler, so every one of them is a real connection against the Neon compute.
# Hence the explicit small pool below rather than SQLAlchemy's 5 + 10 default,
# which would allow 15 concurrent server connections for scoring alone.
#
# If this has to go back onto the pooled URL, the only sound way is a separate
# LOGIN role with its own credentials - a distinct user, not a SET ROLE - since
# the pooler can hand a connection's identity out but cannot hand out a
# different user's login.
_SCORING_URL = settings.DATABASE_URL_DIRECT
_SCORING_POOL_SIZE = 3
_SCORING_MAX_OVERFLOW = 2

engine_app: AsyncEngine = build_engine(_APP_URL, name="DATABASE_URL_POOLED")
engine_scoring: AsyncEngine = build_engine(
    _SCORING_URL,
    scoring_role=settings.DB_SCORING_ROLE,
    pool_size=_SCORING_POOL_SIZE,
    max_overflow=_SCORING_MAX_OVERFLOW,
    name="DATABASE_URL_DIRECT",
)

# expire_on_commit=False: with expire_on_commit=True the ORM discards loaded
# attributes on commit, and a FastAPI handler that commits and then reads
# attributes off the instance raises DetachedInstanceError, because the session
# has already been closed by the dependency's teardown.
SessionApp = async_sessionmaker(engine_app, expire_on_commit=False)
SessionScoring = async_sessionmaker(engine_scoring, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for general database access."""
    async with SessionApp() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_scoring_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for the scoring service only.

    Connections from this session run as settings.DB_SCORING_ROLE, so reads the
    role has not been granted - farmers.gender among them - fail at the
    database. Do not fall back to get_db_session() in scoring code: that would
    silently move the read back to a role that can see the column.
    """
    async with SessionScoring() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def verify_db_connection() -> None:
    """Startup check: fail the boot if engine_app cannot reach the database.

    Called from main.py's lifespan. Without this a bad DATABASE_URL_POOLED
    surfaces as a 500 on the first real request instead of at startup, which
    reads as an application bug rather than a configuration one.
    """
    try:
        async with engine_app.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise RuntimeError(
            "Postgres startup healthcheck failed for engine_app. "
            "Check DATABASE_URL_POOLED in your environment - it must be a "
            "reachable Postgres URL. (The host, database, credentials and ssl "
            "parameters are deliberately not logged.) "
            f"Underlying error: {type(exc).__name__}: {exc}"
        ) from exc

    logger.info("Postgres healthcheck passed (engine_app).")


async def verify_scoring_connection() -> None:
    """Startup check: confirm the scoring role actually took effect.

    `SELECT 1` succeeding says nothing about the role - a connection that
    silently fell back to the login role still answers it, and the scoring path
    would then quietly gain read access to farmers.gender. This asserts the
    identity instead of assuming it.
    """
    try:
        async with engine_scoring.connect() as connection:
            actual_role = (await connection.execute(text("SELECT current_user"))).scalar_one()
    except Exception as exc:
        raise RuntimeError(
            "Postgres startup healthcheck failed for engine_scoring. Check "
            "DATABASE_URL_POOLED and DB_SCORING_ROLE, and confirm the login role "
            "is a member of the scoring role (GRANT app_scoring TO <login role>) "
            "- without that membership the connection is refused at startup, "
            "which is the intended fail-closed behaviour. "
            f"Underlying error: {type(exc).__name__}: {exc}"
        ) from exc

    if actual_role != settings.DB_SCORING_ROLE:
        raise RuntimeError(
            f"engine_scoring connected as {actual_role!r} but DB_SCORING_ROLE is "
            f"{settings.DB_SCORING_ROLE!r}. The scoring role was not applied, so "
            "the scoring path would read data it is meant to be denied. Refusing "
            "to start. If DATABASE_URL_POOLED routes through a transaction-mode "
            "pooler, confirm it forwards the `role` startup parameter."
        )

    logger.info("Postgres healthcheck passed (engine_scoring as %s).", actual_role)


async def dispose_engines() -> None:
    """Close both pools on shutdown so connections are not leaked on reload."""
    await engine_app.dispose()
    await engine_scoring.dispose()


# ===========================================================================
# DEPRECATED - see database.py history, removed after cutover verified
#
# The Neo4j driver below is dead weight once the Postgres path is live, but it
# is kept commented rather than deleted so the cutover stays reversible: restore
# this block and delete the engines above to go back to the graph backend.
#
# Note that repositories/base_repository.py, graph/schema.py and
# scripts/test_farmer.py still import `db` from this module, which is why the
# shim below stays live. It raises on use rather than on import so that these
# modules remain importable during the cutover - once they are ported to
# AsyncSession, delete the shim with this block.
#
# from neo4j import GraphDatabase
# from core.config import settings
#
#
# class Neo4jConnection:
#     def __init__(self):
#         self.driver = GraphDatabase.driver(
#             settings.NEO4J_URI,
#             auth=(
#                 settings.NEO4J_USERNAME,
#                 settings.NEO4J_PASSWORD,
#             ),
#         )
#
#     def close(self):
#         self.driver.close()
#
#
# db = Neo4jConnection()
# ===========================================================================


class _Neo4jRetired:
    """Import-time stand-in for the retired `db` object. See the block above."""

    @property
    def driver(self):
        raise RuntimeError(
            "The Neo4j driver has been commented out of core/database.py. "
            "Port this caller to get_db_session() / get_scoring_session(), or "
            "restore the commented-out Neo4j block to roll back to the graph "
            "backend."
        )


db = _Neo4jRetired()
