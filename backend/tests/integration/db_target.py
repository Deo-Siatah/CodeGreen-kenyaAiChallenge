"""Which database the real-database tests are allowed to touch.

One resolver, so every integration test agrees on the rules. Each test module
imports TEST_URL / REFUSAL from here instead of reading os.environ itself.

Three outcomes, deliberately distinct:

  * unset          -> SKIP. No test-only database is configured.
  * pooler host    -> REFUSE. Not a "skip": see below.
  * host == main   -> REFUSE. The whole point of the variable is to be a
                      different database.

A refusal raises at import time rather than skipping, and that is the important
part. These tests create and drop Postgres roles, run DDL, and write rows. A
silently skipped suite is a suite that quietly stops proving anything while
still reporting green; a refusal is a broken run that gets noticed. Same reason
neither refusal is a skip even though both are "we cannot run": they mean the
configuration is unsafe, not merely absent.
"""

from urllib.parse import urlparse

import pytest

from core.config import settings

# "None" is the only condition that skips. Optional so the app boots without it.
TEST_URL = settings.TEST_DATABASE_URL_DIRECT


def _host(url: str | None) -> str | None:
    return urlparse(url).hostname if url else None


def _refusal_reason(url: str) -> str | None:
    host = _host(url)
    if host and "-pooler" in host:
        return (
            f"TEST_DATABASE_URL_DIRECT points at a pooler host ({host!r}). A "
            "pooled endpoint multiplexes many clients over a few server "
            "connections and does not reset session state between them, which "
            "is what these tests exist to detect: a connection returned to the "
            "pool can come back with the wrong role. Running them through a "
            "pooler would test the pooler, not the pool. Point "
            "TEST_DATABASE_URL_DIRECT at the branch's DIRECT (non-pooler) "
            "endpoint."
        )
    if host and host == _host(settings.DATABASE_URL_DIRECT):
        return (
            f"TEST_DATABASE_URL_DIRECT has the same host as DATABASE_URL_DIRECT "
            f"({host!r}), so it points at main. These tests create and drop roles "
            "and write rows, so that is never acceptable. Point it at a "
            "throwaway branch."
        )
    return None


REFUSAL = _refusal_reason(TEST_URL) if TEST_URL else None

if REFUSAL:
    raise RuntimeError(REFUSAL)


SKIP_REASON = (
    "TEST_DATABASE_URL_DIRECT is not set, so there is no throwaway database to "
    "test against. These tests create and drop a Postgres role and write rows, "
    "so they only run against a throwaway branch you point this setting at, "
    "never main. Set it to the branch's direct (non-pooler) endpoint."
)


def skip_marker() -> pytest.MarkDecorator:
    """`pytestmark` for a module that needs the real database."""
    return pytest.mark.skipif(TEST_URL is None, reason=SKIP_REASON)
