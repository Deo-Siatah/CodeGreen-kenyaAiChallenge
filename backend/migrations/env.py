"""Alembic environment for AgriForesight.

Migrations run against the *direct* Postgres URL, not the pooled one, because
DDL does not belong on a transaction-mode pooler. See `build_migration_url`.

This module is deliberately importable without the `alembic` CLI and without a
database, so that the URL-building logic below can be unit tested offline. See
`_alembic_is_driving`.
"""

import asyncio
import os
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection, URL
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import settings
from core.database import _asyncpg_url, _ssl_connect_args

# Every model module is imported for its side effect: defining a declarative
# class is what registers its table on Base.metadata. A model whose module is
# not imported here is invisible to autogenerate, which then emits a revision
# that tries to CREATE TABLE for a table the application already queries - so
# these imports must stay above the `target_metadata` assignment, and any new
# model module must be added to this list.
#
# `import models` alone would work today, because models/__init__.py re-exports
# every module, but naming them explicitly means a trimmed or reworked
# __init__.py cannot silently drop a model out of autogenerate.
from models import (  # noqa: F401  (imported for the metadata side effect)
    audit,
    credibility,
    farmer,
    links,
    loan,
    scoring,
    signals,
    trust,
    verification,
)
from models.base import Base

# The single source of truth for "what the schema should look like". Alembic
# diffs this against the live database to decide what a revision contains.
target_metadata = Base.metadata


def resolve_target_url() -> str:
    """Which database this run is for, and prove it before touching anything.

    Resolution order, most explicit first:

      1. `alembic -x dburl=...`      per-invocation, cannot be forgotten
      2. ALEMBIC_DATABASE_URL       per-shell, e.g. for a throwaway branch
      3. settings.DATABASE_URL_DIRECT   the default, and the app's own database

    (1) and (2) exist because option (3) is a footgun on its own. env.py used to
    read DATABASE_URL_DIRECT unconditionally, so migrating a throwaway branch
    meant overriding that variable in the environment - which is easy to get
    wrong, and fails open: get it wrong in the direction that leaves the real
    value in place and the migration lands on main with no complaint. An
    explicit target has to be named on purpose, and is logged before any
    connection is opened.

    The URL is returned raw, not as a SQLAlchemy URL, so the same string is used
    for the host check below and for the connection.
    """
    # -x values arrive as a list because an argument may be repeated. Skipped
    # when Alembic is not driving, so that importing this module to test it does
    # not explode on an unresolvable context proxy.
    if _alembic_is_driving():
        for value in context.get_x_argument(as_dictionary=False):
            if value.startswith("dburl="):
                return value[len("dburl=") :]

    from_env = os.environ.get("ALEMBIC_DATABASE_URL")
    if from_env:
        return from_env

    return settings.DATABASE_URL_DIRECT


def build_migration_url() -> URL:
    """The asyncpg URL Alembic should connect with.

    Built from an explicit target rather than read out of alembic.ini, so the
    database is configured in exactly one place per invocation and alembic.ini
    can be committed without a credential in it.

    Why the target must be a direct URL and never a pooled one: a
    transaction-mode pooler - PgBouncer in `transaction` mode, which is what a
    Neon pooled URL points at - multiplexes many clients over a few server
    connections and does not reset session state between clients. DDL is exactly
    what it mishandles: an implicit transaction wrapper around a migration can
    commit or abandon work on a server connection that the next client is about
    to borrow, so `CREATE TABLE`/`ALTER TABLE` can land on the wrong session, or
    a failed migration can leave a half-applied schema. Alembic's own
    bookkeeping is vulnerable to the same problem, because `alembic_version` is
    just another table. Migrations also have no business pooling at all - they
    are a short-lived one-shot admin task, so they use NullPool below.

    _asyncpg_url() and _ssl_connect_args() are reused from core/database.py so
    the migration connection is constructed exactly like the application
    connection: libpq-only query params (sslmode, channel_binding) stripped,
    which asyncpg would reject as unexpected keyword arguments, and the driver
    set to asyncpg.
    """
    return _asyncpg_url(resolve_target_url(), "ALEMBIC_DATABASE_URL")


def assert_target_is_direct() -> None:
    """Refuse a pooled target, and say which host was rejected.

    A pooled URL is caught here rather than producing a mysterious half-applied
    migration halfway through, which is the outcome the previous paragraph
    describes. Refusing up front also means the rejection is a one-line error
    rather than a puzzle: the host is printed, and only the host - a credential
    in a log line outlives the log.
    """
    # _asyncpg_url only rewrites the driver and strips libpq query params, so
    # the host it reports is the host that will actually be connected to.
    host = _asyncpg_url(resolve_target_url(), "ALEMBIC_DATABASE_URL").host
    if host and "-pooler" in host:
        raise RuntimeError(
            f"Refusing to run migrations against pooled host {host!r}. "
            "Transaction-mode pooling does not reset session state between "
            "clients, so DDL and the alembic_version bookkeeping it depends on "
            "can land on the wrong server connection. Point -x dburl=... (or "
            "ALEMBIC_DATABASE_URL) at a direct, non-pooler endpoint."
        )
    print(f"[alembic] target host: {host!r}")


def build_engine_kwargs() -> dict[str, Any]:
    """Engine options for the migration connection.

    NullPool rather than a real pool: a migration is a one-shot admin task, and
    pooling DDL connections only risks handing a later migration a connection
    with session state still set from the previous one. `ssl` is passed through
    connect_args the same way build_engine() does it in core/database.py,
    because asyncpg takes the libpq `sslmode` under a different name and will
    not accept it as a URL query parameter.
    """
    return {
        "poolclass": pool.NullPool,
        "connect_args": _ssl_connect_args(
            resolve_target_url(), "ALEMBIC_DATABASE_URL"
        ),
    }


def _alembic_is_driving() -> bool:
    """True when this module was executed by the `alembic` CLI.

    `alembic.context` is a proxy that only resolves while an EnvironmentContext
    is established, so `context.is_offline_mode()` raises NameError when env.py
    is merely imported. That is what makes the guard below necessary: tests
    import build_migration_url() to check the URL handling without a database,
    and without this check that import would blow up before reaching it.
    """
    try:
        context.is_offline_mode()
    except NameError:
        return False
    return True


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to a database."""
    assert_target_is_direct()
    context.configure(
        url=build_migration_url().render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Detect column type and server-default drift, not just added/dropped
        # columns. Without compare_type a column changed from VARCHAR to TEXT,
        # or INTEGER to BIGINT, autogenerate sees no difference and silently
        # leaves the model and the database disagreeing. The same applies to
        # server defaults: a default changed only in the model would otherwise
        # never produce a migration.
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Connect with asyncpg and run the migrations on that connection."""
    connectable = create_async_engine(build_migration_url(), **build_engine_kwargs())

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        # Disposed in a finally so a failed migration does not leave the
        # process holding a connection to the database it just failed against.
        await connectable.dispose()


def run_migrations_online() -> None:
    # Before any connection: refuse a pooled target, and print the host so the
    # run can be confirmed against the intended database after the fact.
    assert_target_is_direct()
    asyncio.run(run_async_migrations())


if _alembic_is_driving():
    _config = context.config
    if _config.config_file_name is not None and _config.attributes.get(
        "configure_logger", True
    ):
        fileConfig(_config.config_file_name)

    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
