r"""
Unit tests: engine construction and startup-failure behaviour in
`core/database.py`. No database and no network required.

These cover what can be decided without a live Postgres: how a URL is
normalised before it reaches asyncpg, that the scoring role is wired into the
connect kwargs, and that a misconfigured URL produces an actionable error
instead of a driver traceback.

The tests that genuinely need a server -- that a session can run `SELECT 1`, and
that the scoring session really arrives as `app_scoring` -- live in
tests/integration/test_database_sessions.py. Asserting those against a mocked
driver would only prove the mock returns what it was told to return.

HOW TO RUN
----------
All commands run from the `backend/` directory (the one holding
pyproject.toml, not the repo root):

    cd backend
    uv run pytest tests/unit/core/test_database_engine.py -v

WHY THE ROLE IS ASSERTED ON THE CONNECT KWARGS, NOT ON A SESSION
-----------------------------------------------------------------
`current_user` only becomes `app_scoring` once a server has accepted the
startup message; there is no offline way to observe that. So this file asserts
the mechanism -- that `role` reaches asyncpg.connect() -- and the integration
file asserts the effect. verify_scoring_connection() is what enforces it at
boot.
"""

import asyncpg
import inspect
import pytest
from sqlalchemy.exc import DisconnectionError

import core.database as database
from core.config import settings

# Reachable-shaped, but used only where asyncpg.connect is intercepted.
_VALID_URL = "postgresql://u:p@db.invalid:5432/db?sslmode=require&channel_binding=require"
# 127.0.0.1:1 is a closed port, so the failure paths get an instant
# ECONNREFUSED. A non-resolving hostname like db.invalid works too but costs
# seconds of DNS timeout per test, which is why this one is not used there.
_GARBAGE_URL = "postgresql://u:p@127.0.0.1:1/db?sslmode=require"


# ---------------------------------------------------------------------------
# URL normalisation
# ---------------------------------------------------------------------------


def test_libpq_only_params_are_stripped_from_the_url():
    """`sslmode` / `channel_binding` must not survive into asyncpg.connect().

    SQLAlchemy merges the URL query straight into connect() as keyword
    arguments and asyncpg's connect() accepts neither name, so a URL carrying
    them raises TypeError on the first real connection.
    """
    url = database._asyncpg_url(_VALID_URL)

    assert "sslmode" not in url.query
    assert "channel_binding" not in url.query


def test_drivername_is_rewritten_to_the_asyncpg_dialect():
    assert database._asyncpg_url("postgresql://u:p@host/db").drivername == (
        "postgresql+asyncpg"
    )


def test_sync_psycopg_drivername_is_rewritten_too():
    """DATABASE_URL_DIRECT is a libpq URL; a psycopg scheme must not be handed to
    the asyncpg engine."""
    url = database._asyncpg_url("postgresql+psycopg://u:p@host/db")

    assert url.drivername == "postgresql+asyncpg"


def test_sslmode_is_carried_across_as_the_asyncpg_ssl_argument():
    """asyncpg spells libpq's `sslmode` as `ssl` and accepts the mode string
    directly, so the value transfers without reinterpretation."""
    args = database._ssl_connect_args(_VALID_URL)

    assert args == {"ssl": "require"}


def test_no_ssl_args_when_the_url_has_no_sslmode():
    assert database._ssl_connect_args("postgresql://u:p@host/db") == {}


@pytest.mark.parametrize(
    "bad_url",
    [
        pytest.param("not a url at all", id="unparseable"),
        pytest.param("mysql://u:p@host/db", id="wrong-dialect"),
    ],
)
def test_unusable_url_raises_a_readable_error(bad_url):
    """A wrong URL should say what is wrong, not leak a URL-dialect error."""
    with pytest.raises(ValueError) as excinfo:
        database.build_engine(bad_url, name="DATABASE_URL_POOLED")

    assert "DATABASE_URL_POOLED" in str(excinfo.value)


@pytest.mark.parametrize("setting", ["DATABASE_URL_POOLED", "DATABASE_URL_DIRECT"])
def test_parse_url_error_names_the_setting_it_was_given(setting):
    """A bad DATABASE_URL_DIRECT must be reported as such, not blamed on
    DATABASE_URL_POOLED."""
    with pytest.raises(ValueError) as excinfo:
        database._parse_url("mysql://u:p@host/db", name=setting)

    assert str(excinfo.value).startswith(setting)


def test_parse_url_error_on_unparseable_url_names_the_setting():
    with pytest.raises(ValueError) as excinfo:
        database._parse_url("not a url at all", name="DATABASE_URL_DIRECT")

    assert "DATABASE_URL_DIRECT" in str(excinfo.value)


def test_parse_url_defaults_to_a_generic_name():
    """The default must not silently claim to be DATABASE_URL_POOLED."""
    with pytest.raises(ValueError) as excinfo:
        database._parse_url("mysql://u:p@host/db")

    message = str(excinfo.value)
    assert "DATABASE_URL_POOLED" not in message
    assert "Postgres URL" in message


# ---------------------------------------------------------------------------
# Pool sizing
# ---------------------------------------------------------------------------


def test_build_engine_forwards_pool_size_and_max_overflow():
    engine = database.build_engine(
        _VALID_URL, pool_size=3, max_overflow=2
    )

    assert engine.pool.size() == 3
    assert engine.pool._max_overflow == 2


def test_build_engine_omits_pool_args_when_none():
    """None must mean "use SQLAlchemy's defaults", not pin them to None."""
    engine = database.build_engine(_VALID_URL)

    # SQLAlchemy's QueuePool defaults: 5 kept, 10 overflow.
    assert engine.pool.size() == 5
    assert engine.pool._max_overflow == 10


def test_build_engine_omits_only_the_args_left_as_none():
    engine = database.build_engine(_VALID_URL, pool_size=2)

    assert engine.pool.size() == 2
    assert engine.pool._max_overflow == 10


def test_scoring_engine_uses_the_configured_pool_size():
    """5 real server connections max (3 kept + 2 overflow) against a small
    Neon compute, rather than SQLAlchemy's 15."""
    assert database._SCORING_POOL_SIZE == 3
    assert database._SCORING_MAX_OVERFLOW == 2

    pool = database.engine_scoring.pool
    assert pool.size() == database._SCORING_POOL_SIZE
    assert pool._max_overflow == database._SCORING_MAX_OVERFLOW


def test_app_engine_is_left_on_default_pool_sizing():
    """Only the scoring pool is constrained; the pooled app engine is not."""
    pool = database.engine_app.pool

    assert pool.size() == 5
    assert pool._max_overflow == 10


# ---------------------------------------------------------------------------
# Role wiring
# ---------------------------------------------------------------------------


async def _connect_kwargs(engine) -> dict:
    """The exact kwargs the dialect will hand to asyncpg.connect().

    Intercepts the driver call rather than reading the engine's internals, so
    this fails if SQLAlchemy's connect_args/URL merge ever stops producing what
    the driver needs.
    """
    captured = {}
    real_connect = asyncpg.connect

    async def fake_connect(*args, **kwargs):
        captured.update(kwargs)
        raise _Unreachable

    asyncpg.connect = fake_connect
    try:
        try:
            await engine.connect()
        except Exception:
            pass
    finally:
        asyncpg.connect = real_connect

    return captured


async def test_scoring_engine_runs_set_role_on_connect():
    """The role must be applied by a statement, not a startup parameter.

    Sending `role` as a startup-message parameter looks tidier and is silently
    ignored by PostgreSQL - the connection succeeds and quietly runs as the
    login role. Measured on this project's own database.
    """
    calls = _run_connect_listener(
        database.build_engine(_VALID_URL), "app_scoring"
    )

    assert calls[0] == 'SET ROLE "app_scoring"'


async def test_connect_listener_commits_the_set_role():
    """The commit is the whole point of this listener.

    The asyncpg adapter opens an implicit transaction for any cursor execute,
    so an uncommitted SET ROLE is reverted when SQLAlchemy rolls the
    connection back on pool return. A scoring session that only reads never
    commits, so without this the first checkout would run as the scoring role
    and every later one as the login role - which can read farmers.gender.
    """
    calls = _run_connect_listener(
        database.build_engine(_VALID_URL), "app_scoring"
    )

    assert calls == ['SET ROLE "app_scoring"', "commit"], (
        "SET ROLE must be followed by a commit, and in that order"
    )


async def test_checkout_listener_is_quiet_when_the_role_matches():
    calls = _run_checkout_listener(
        database.build_engine(_VALID_URL), "app_scoring", current_user="app_scoring"
    )

    assert calls == ["SELECT current_user", "commit"]


async def test_checkout_listener_raises_when_the_role_drifted():
    """The fail-closed half.

    A connection that came back as the login role must never be handed to a
    caller. Raising DisconnectionError makes the pool invalidate and retry
    (Pool._checkout catches it) rather than serve the wrong role.
    """
    with pytest.raises(DisconnectionError) as excinfo:
        _run_checkout_listener(
            database.build_engine(_VALID_URL),
            "app_scoring",
            current_user="neondb_owner",
        )

    message = str(excinfo.value)
    assert "neondb_owner" in message
    assert "app_scoring" in message


async def test_checkout_listener_raises_when_the_role_query_returns_nothing():
    """A NULL/empty result is drift too, not a pass."""
    with pytest.raises(DisconnectionError):
        _run_checkout_listener(
            database.build_engine(_VALID_URL), "app_scoring", current_user=None
        )


async def test_checkout_listener_re_reads_the_role_on_every_checkout():
    """Drift can happen after the connection was first set up, so the check has
    to be per-checkout rather than once at connect."""
    engine = database.build_engine(_VALID_URL)
    listener = database._apply_role_on_connect(engine, "app_scoring")

    for _ in range(3):
        calls = _Calls()
        listener.checkout(_FakeDBAPIConnection(calls, "app_scoring"), None, None)
        assert calls == ["SELECT current_user", "commit"]


async def test_apply_role_on_connect_returns_both_listeners():
    """Tests drive the listeners directly, so both have to be reachable."""
    engine = database.build_engine(_VALID_URL)

    listeners = database._apply_role_on_connect(engine, "app_scoring")

    assert callable(listeners.connect)
    assert callable(listeners.checkout)


async def test_build_engine_registers_the_role_listener(monkeypatch):
    registered: list[str] = []

    def _spy(engine, role):
        registered.append(role)
        return database._RoleListeners(lambda *_: None, lambda *_: None)

    monkeypatch.setattr(database, "_apply_role_on_connect", _spy)

    database.build_engine(_VALID_URL, scoring_role="app_scoring")
    assert registered == ["app_scoring"]

    registered.clear()
    database.build_engine(_VALID_URL)
    assert registered == [], "the general engine must not have a role forced onto it"


def test_scoring_role_identifier_is_quoted():
    """DB_SCORING_ROLE is interpolated into a SET ROLE statement, so a value
    containing a quote must not be able to break out of the identifier."""
    calls = _run_connect_listener(
        database.build_engine(_VALID_URL), 'evil"; DROP TABLE x; --'
    )

    assert calls[0] == 'SET ROLE "evil""; DROP TABLE x; --"'


async def test_scoring_engine_does_not_use_the_pooled_url():
    """The pooler does not reset session state between clients, so SET ROLE
    there would leak roles sideways between requests.

    Measured on this project's own .env: a GUC set by one client is still set
    for the next client on the pooled URL, and correctly gone on the direct
    URL. This test is the guard on that finding - if the scoring engine is ever
    moved back onto the pooled URL, the role boundary silently stops holding.
    """
    from sqlalchemy.engine import make_url

    direct = make_url(settings.DATABASE_URL_DIRECT)

    assert database.engine_scoring.url != database.engine_app.url
    assert database.engine_scoring.url.host == direct.host
    assert database.engine_scoring.url.database == database.engine_app.url.database


async def test_no_connect_kwarg_is_rejected_by_asyncpg():
    """Guards the TypeError described in the module docstring: any connect kwarg
    SQLAlchemy produces here must be a real asyncpg.connect() parameter, or the
    first real request dies."""
    import inspect as _inspect

    accepted = set(_inspect.signature(asyncpg.connect).parameters)

    for role in (None, "app_scoring"):
        kwargs = await _connect_kwargs(
            database.build_engine(_VALID_URL, scoring_role=role)
        )
        assert set(kwargs) <= accepted, f"unexpected kwargs: {set(kwargs) - accepted}"


async def test_scoring_and_app_engines_are_distinct_objects():
    assert database.engine_scoring is not database.engine_app


# ---------------------------------------------------------------------------
# Startup failure behaviour
# ---------------------------------------------------------------------------


async def test_verify_db_connection_raises_a_clear_error_for_a_garbage_url(monkeypatch):
    """A typo'd DATABASE_URL_POOLED must name the setting and the reason.

    This is the boot-time contract: main.py's lifespan calls
    verify_db_connection() and lets the exception fail startup. An opaque
    OSError traceback here would send whoever is on call looking at app code
    instead of at config.
    """
    monkeypatch.setattr(database, "engine_app", database.build_engine(_GARBAGE_URL))

    with pytest.raises(RuntimeError) as excinfo:
        await database.verify_db_connection()

    message = str(excinfo.value)
    assert "DATABASE_URL_POOLED" in message
    assert "healthcheck failed" in message
    # The wrapped cause is preserved for debugging...
    assert excinfo.value.__cause__ is not None
    # ...but the message must not echo credentials back out.
    assert "127.0.0.1" not in message


async def test_verify_db_connection_error_names_the_engine(monkeypatch):
    monkeypatch.setattr(database, "engine_app", database.build_engine(_GARBAGE_URL))

    with pytest.raises(RuntimeError, match="engine_app"):
        await database.verify_db_connection()


async def test_verify_scoring_connection_raises_when_connection_fails(monkeypatch):
    monkeypatch.setattr(
        database, "engine_scoring", database.build_engine(_GARBAGE_URL, scoring_role="app_scoring")
    )

    with pytest.raises(RuntimeError, match="engine_scoring"):
        await database.verify_scoring_connection()


async def test_verify_scoring_connection_refuses_to_start_on_role_mismatch(monkeypatch):
    """`SELECT 1` succeeding proves nothing about the role.

    If the pooler drops the `role` startup parameter the connection silently
    falls back to the login role and the scoring path regains read access to
    farmers.gender. Boot must stop rather than continue in that state.
    """
    monkeypatch.setattr(
        database, "engine_scoring", _engine_reporting_current_user("some_login_role")
    )

    with pytest.raises(RuntimeError) as excinfo:
        await database.verify_scoring_connection()

    message = str(excinfo.value)
    assert "some_login_role" in message
    assert settings.DB_SCORING_ROLE in message
    assert "Refusing to start" in message


async def test_verify_scoring_connection_passes_when_role_is_applied(monkeypatch):
    monkeypatch.setattr(
        database, "engine_scoring", _engine_reporting_current_user(settings.DB_SCORING_ROLE)
    )

    await database.verify_scoring_connection()  # must not raise


# ---------------------------------------------------------------------------
# Session dependency shape
#
# These run offline. They do not prove the sessions work against Postgres --
# that is the integration suite's job -- but they pin the dependency
# generator's contract, so a change that breaks it fails here with a clear
# message instead of turning every integration test into a false pass or a
# confusing error.
# ---------------------------------------------------------------------------


async def test_get_db_session_is_an_async_generator():
    assert inspect.isasyncgenfunction(database.get_db_session)


async def test_get_scoring_session_is_an_async_generator():
    assert inspect.isasyncgenfunction(database.get_scoring_session)


async def test_get_db_session_rolls_back_when_the_handler_raises(monkeypatch):
    """A handler that raises must not leave the transaction open for the pool.

    `athrow` is how FastAPI reports a handler exception into a dependency
    generator, so this drives the real code path rather than simulating it.
    """
    calls = _record_session_calls(monkeypatch, "SessionApp")

    generator = database.get_db_session()
    await generator.__anext__()
    with pytest.raises(RuntimeError, match="boom"):
        await generator.athrow(RuntimeError("boom"))

    assert calls == ["rollback", "close"]


async def test_scoring_session_rolls_back_when_the_handler_raises(monkeypatch):
    calls = _record_session_calls(monkeypatch, "SessionScoring")

    generator = database.get_scoring_session()
    await generator.__anext__()
    with pytest.raises(RuntimeError, match="boom"):
        await generator.athrow(RuntimeError("boom"))

    assert calls == ["rollback", "close"]


async def test_session_dependency_closes_on_normal_exit(monkeypatch):
    """The happy path must also close, or every request leaks a connection."""
    calls = _record_session_calls(monkeypatch, "SessionApp")

    generator = database.get_db_session()
    await generator.__anext__()
    await generator.aclose()

    assert calls == ["close"]


async def test_scoring_session_dependency_uses_the_scoring_sessionmaker(monkeypatch):
    """The scoring dependency must not fall back to the general sessionmaker --
    that would silently hand scoring code a connection that can read
    farmers.gender.

    Behavioural rather than source-inspecting: both factories are recorded and
    the test asserts which one the dependency actually reached for.
    """
    used = _record_both_session_calls(monkeypatch)

    generator = database.get_scoring_session()
    await generator.__anext__()
    await generator.aclose()

    assert used == ["SessionScoring"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record_both_session_calls(monkeypatch) -> list[str]:
    """Record which of the two sessionmakers a dependency reaches for."""
    used: list[str] = []

    class _Recorder:
        async def rollback(self):
            ...

        async def close(self):
            ...

    class _SessionCM:
        async def __aenter__(self):
            return _Recorder()

        async def __aexit__(self, *exc_info):
            return False

    for name in ("SessionApp", "SessionScoring"):
        monkeypatch.setattr(
            database, name, _LabelledFactory(name, used, _SessionCM)
        )
    return used


class _LabelledFactory:
    def __init__(self, name, used, cm_class):
        self._name = name
        self._used = used
        self._cm_class = cm_class

    def __call__(self):
        self._used.append(self._name)
        return self._cm_class()


class _Calls(list):
    """The operations a listener performed, in order, plus the row its
    SELECT is expected to return."""

    fetchone_result: tuple | None = None


class _RecordingCursor:
    def __init__(self, calls: _Calls):
        self._calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, statement):
        self._calls.append(statement)

    def fetchone(self):
        return self._calls.fetchone_result


class _FakeDBAPIConnection:
    def __init__(self, calls: _Calls, current_user: str | None = None):
        self._calls = calls
        self._calls.fetchone_result = (current_user,) if current_user else None

    def cursor(self):
        return _RecordingCursor(self._calls)

    def commit(self):
        self._calls.append("commit")

    def rollback(self):
        self._calls.append("rollback")


def _run_connect_listener(engine, role: str) -> _Calls:
    """Run the connect listener against a recording connection; return the calls.

    Mirrors what the pool does when it opens a raw connection, so it exercises
    the real listener rather than asserting on how it was written.
    """
    calls = _Calls()
    listener = database._apply_role_on_connect(engine, role)
    listener.connect(_FakeDBAPIConnection(calls), None)
    return calls


def _run_checkout_listener(engine, role: str, current_user: str | None) -> _Calls:
    calls = _Calls()
    listener = database._apply_role_on_connect(engine, role)
    listener.checkout(_FakeDBAPIConnection(calls, current_user), None, None)
    return calls


def _record_session_calls(monkeypatch, factory_attr: str) -> list[str]:
    """Point a sessionmaker at a recorder; returns the list it appends to."""
    calls: list[str] = []

    class _Recorder:
        async def rollback(self):
            calls.append("rollback")

        async def close(self):
            calls.append("close")

    class _SessionCM:
        async def __aenter__(self):
            return _Recorder()

        async def __aexit__(self, *exc_info):
            await _Recorder().close()
            return False

    monkeypatch.setattr(database, factory_attr, lambda: _SessionCM())
    return calls


class _Unreachable(Exception):
    """Stands in for a network error so connect attempts fail fast offline."""


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class _FakeConnection:
    def __init__(self, current_user):
        self._current_user = current_user

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def execute(self, statement):
        return _FakeResult(self._current_user)


class _FakeEngine:
    """Answers `SELECT current_user` with a fixed value, as Postgres would."""

    def __init__(self, current_user):
        self._current_user = current_user

    def connect(self):
        return _FakeConnection(self._current_user)


def _engine_reporting_current_user(current_user: str) -> _FakeEngine:
    return _FakeEngine(current_user)
