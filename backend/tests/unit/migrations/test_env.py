"""Tests for migrations/env.py's connection-string handling.

These import env.py directly instead of shelling out to the `alembic` CLI,
because the point is to check URL construction with no database in sight. No
test here opens a connection.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[3]
ENV_PY = BACKEND_ROOT / "migrations" / "env.py"

# A realistic Neon URL. The sslmode/channel_binding pair is the whole point:
# those are libpq parameters that asyncpg does not accept, and they arrive on
# every Neon connection string in this project's .env.
NEON_DIRECT_URL = (
    "postgresql://app_owner:s3cret@ep-olive-bird-a1b2c3d4.us-east-2.aws.neon.tech"
    "/neondb?sslmode=require&channel_binding=prefer"
)
NEON_POOLED_URL = (
    "postgresql://app_owner:s3cret@ep-olive-bird-a1b2c3d4-pooler.us-east-2.aws.neon.tech"
    "/neondb?sslmode=require&channel_binding=prefer"
)
# A throwaway branch, on its own direct endpoint. Deliberately not "-pooler".
NEON_BRANCH_URL = (
    "postgresql://app_owner:s3cret@ep-olive-bird-b7c8d9e0.us-east-2.aws.neon.tech"
    "/neondb?sslmode=require&channel_binding=prefer"
)


@pytest.fixture(scope="module")
def env_module():
    """Load migrations/env.py as a module.

    Loading it at all is part of what is under test: env.py normally executes
    migrations the moment it is imported, which would need a live database.
    """
    spec = importlib.util.spec_from_file_location("migrations_env_under_test", ENV_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


@pytest.fixture
def direct_settings(env_module, monkeypatch):
    """Point both settings at known Neon URLs, returning the settings object."""
    monkeypatch.setattr(env_module.settings, "DATABASE_URL_DIRECT", NEON_DIRECT_URL, raising=False)
    monkeypatch.setattr(env_module.settings, "DATABASE_URL_POOLED", NEON_POOLED_URL, raising=False)
    return env_module.settings


def test_build_migration_url_is_asyncpg_without_libpq_params(env_module, direct_settings):
    """The core requirement: a usable asyncpg URL, no libpq-only params left."""
    url = env_module.build_migration_url()

    assert url.drivername == "postgresql+asyncpg"
    assert "sslmode" not in url.query
    assert "channel_binding" not in url.query


def test_build_migration_url_keeps_the_rest_of_the_url_intact(env_module, direct_settings):
    """Stripping must not damage host, credentials, database or port."""
    url = env_module.build_migration_url()

    assert url.host == "ep-olive-bird-a1b2c3d4.us-east-2.aws.neon.tech"
    assert url.database == "neondb"
    assert url.username == "app_owner"
    assert url.password == "s3cret"


def test_build_migration_url_uses_the_direct_url_not_the_pooled_one(env_module, direct_settings):
    """DDL must not go through the transaction-mode pooler.

    The two URLs differ only by host, so a regression to DATABASE_URL_POOLED
    would otherwise be invisible to the other assertions in this file.
    """
    url = env_module.build_migration_url()

    assert url.host == "ep-olive-bird-a1b2c3d4.us-east-2.aws.neon.tech"
    assert "-pooler" not in url.host
    assert url.host != direct_settings.DATABASE_URL_POOLED.split("@")[1].split("/")[0]


def test_build_engine_kwargs_passes_sslmode_through_connect_args(env_module, direct_settings):
    """sslmode is renamed for asyncpg via connect_args, as build_engine does.

    Dropping sslmode from the query without re-supplying it would silently
    connect unencrypted, so this pins that the value is not just removed.
    """
    kwargs = env_module.build_engine_kwargs()

    assert kwargs["connect_args"] == {"ssl": "require"}


def test_env_py_registers_every_model_module_on_metadata(env_module):
    """target_metadata must cover the models, or autogenerate emits nonsense.

    A model module that is not imported in env.py is invisible to autogenerate,
    which would then generate CREATE TABLE for a table the app already uses.
    """
    tables = env_module.target_metadata.tables

    assert env_module.target_metadata is not None
    # Spot-check across the modules named in the import block, rather than
    # pinning all 23 tables, which would turn every model change into a
    # failure here as well as in the models' own tests.
    for expected in (
        "farmers",
        "trust_sources",
        "farmer_trust_source_links",
        "verification_sessions",
        "farm_activity_signals",
        "score_profiles",
        "verifier_credibility",
        "audit_logs",
        "loans",
    ):
        assert expected in tables, f"{expected} missing from target_metadata"


# ---------------------------------------------------------------------------
# Explicit migration target
# ---------------------------------------------------------------------------


def test_falls_back_to_database_url_direct(env_module, direct_settings, monkeypatch):
    """With nothing explicit set, the target is the app's own database."""
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)

    assert env_module.resolve_target_url() == NEON_DIRECT_URL


def test_alembic_database_url_env_var_wins_over_the_fallback(
    env_module, direct_settings, monkeypatch
):
    """The per-shell override exists so a branch can be migrated without
    impersonating the app's own configuration."""
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", NEON_BRANCH_URL)

    assert env_module.resolve_target_url() == NEON_BRANCH_URL
    assert env_module.build_migration_url().host == "ep-olive-bird-b7c8d9e0.us-east-2.aws.neon.tech"


def test_dburl_argument_wins_over_the_env_var(
    env_module, direct_settings, monkeypatch
):
    """-x is the most explicit form and must beat everything else.

    -x is per-invocation, so it cannot be left over in a shell profile the way
    an exported variable can.
    """
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", NEON_BRANCH_URL)
    monkeypatch.setattr(
        env_module, "_alembic_is_driving", lambda: True
    )
    monkeypatch.setattr(
        env_module.context, "get_x_argument", lambda as_dictionary=False: [
            f"dburl={NEON_BRANCH_URL}"
        ]
    )

    assert env_module.resolve_target_url() == NEON_BRANCH_URL


def test_dburl_argument_is_ignored_when_alembic_is_not_driving(
    env_module, direct_settings, monkeypatch
):
    """Importing env.py to test it must not try to read the Alembic context.

    context is a proxy that only resolves while Alembic is driving, so an
    unguarded get_x_argument() would raise NameError on import.
    """
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)
    monkeypatch.setattr(env_module, "_alembic_is_driving", lambda: False)

    assert env_module.resolve_target_url() == NEON_DIRECT_URL


def test_pooled_target_is_refused(env_module, monkeypatch):
    """A pooled target must be rejected before any connection is opened.

    The host is named in the error, so the rejection is diagnosable, and no
    credential appears in the message.
    """
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", NEON_POOLED_URL)

    with pytest.raises(RuntimeError) as excinfo:
        env_module.assert_target_is_direct()

    message = str(excinfo.value)
    assert "-pooler" in message
    assert "s3cret" not in message, "the error must not leak the password"
    assert "app_owner" not in message, "the error must not leak the username"


def test_direct_target_is_accepted_and_its_host_logged(
    env_module, monkeypatch, capsys
):
    """A direct target passes, and the host is printed so the run is auditable.

    Only the host is printed - a credential in a log line outlives the log.
    """
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", NEON_DIRECT_URL)

    env_module.assert_target_is_direct()

    out = capsys.readouterr().out
    assert "ep-olive-bird-a1b2c3d4.us-east-2.aws.neon.tech" in out
    assert "s3cret" not in out

