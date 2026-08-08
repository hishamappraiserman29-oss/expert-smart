"""
test_database_connection.py — direct tests for database/connection.py::get_db().

Wave 4B2 runtime-blocker fix: get_db() was a bare generator with no
@contextlib.contextmanager decorator, so `with get_db() as db:` — the usage
documented in its own docstring and used throughout bridge_api.py — raised
TypeError unconditionally, before ever attempting to reach a database.

These tests exercise the real, unmodified `core_engine.database.connection.get_db`
context-manager protocol directly. They do not connect to or mutate any
database: the underlying session provider (`get_session_factory`) is
monkeypatched to a deterministic in-memory fake, exactly as this module's own
lazy-singleton design already anticipates for tests (`_SessionLocal`/
`get_session_factory()` are not called until first use).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))
    import database.connection as db_connection
finally:
    os.chdir(_ORIG_CWD)


class _FakeSession:
    """Minimal stand-in for a SQLAlchemy Session — no DB connection involved."""

    def __init__(self):
        self.closed = False
        self.commits = 0
        self.rollbacks = 0

    def close(self):
        self.closed = True

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.fixture()
def fake_session(monkeypatch):
    """
    Replace get_session_factory() so get_db() never touches a real engine/DB.
    get_db() itself (the function under test) is NOT replaced or wrapped —
    only the session provider it calls internally.
    """
    session = _FakeSession()
    monkeypatch.setattr(db_connection, "get_session_factory", lambda: (lambda: session))
    return session


# ---------------------------------------------------------------------------
# Protocol support
# ---------------------------------------------------------------------------

def test_conn_01_get_db_returns_a_real_context_manager(fake_session):
    """get_db() must return an object implementing __enter__/__exit__."""
    cm = db_connection.get_db()
    assert hasattr(cm, "__enter__")
    assert hasattr(cm, "__exit__")


def test_conn_02_with_statement_does_not_raise_typeerror(fake_session):
    """The exact production usage pattern must not raise TypeError."""
    with db_connection.get_db() as db:
        assert db is fake_session


# ---------------------------------------------------------------------------
# Session acquisition / yield
# ---------------------------------------------------------------------------

def test_conn_03_session_is_yielded_to_caller(fake_session):
    with db_connection.get_db() as db:
        assert db is fake_session


def test_conn_04_caller_can_use_yielded_session(fake_session):
    with db_connection.get_db() as db:
        db.commit()
    assert fake_session.commits == 1


# ---------------------------------------------------------------------------
# Cleanup on normal exit
# ---------------------------------------------------------------------------

def test_conn_05_cleanup_occurs_on_normal_exit(fake_session):
    assert fake_session.closed is False
    with db_connection.get_db() as db:
        pass
    assert fake_session.closed is True


# ---------------------------------------------------------------------------
# Cleanup + exception propagation when the body raises
# ---------------------------------------------------------------------------

def test_conn_06_cleanup_occurs_when_body_raises(fake_session):
    assert fake_session.closed is False
    with pytest.raises(ValueError):
        with db_connection.get_db() as db:
            raise ValueError("body failure")
    assert fake_session.closed is True


def test_conn_07_body_exception_is_not_swallowed(fake_session):
    """The original exception type and message must propagate unchanged."""
    with pytest.raises(ValueError, match="specific failure reason"):
        with db_connection.get_db() as db:
            raise ValueError("specific failure reason")


def test_conn_08_non_value_error_exception_also_propagates(fake_session):
    """Cleanup must not convert an unrelated exception type into success or a different type."""
    with pytest.raises(RuntimeError, match="unrelated failure"):
        with db_connection.get_db() as db:
            raise RuntimeError("unrelated failure")


# ---------------------------------------------------------------------------
# get_db() does not itself invoke rollback/commit — no new semantics added
# ---------------------------------------------------------------------------

def test_conn_09_get_db_does_not_auto_rollback_on_exception(fake_session):
    """
    get_db() has no rollback call before or after this fix — it only
    guarantees close(). Callers (db_writer.py) are responsible for their own
    rollback on error, exactly as before. This proves the fix did not add
    new transaction semantics.
    """
    with pytest.raises(ValueError):
        with db_connection.get_db() as db:
            raise ValueError("boom")
    assert fake_session.rollbacks == 0


def test_conn_10_get_db_does_not_auto_commit(fake_session):
    """get_db() must not commit on behalf of the caller."""
    with db_connection.get_db() as db:
        pass
    assert fake_session.commits == 0


# ---------------------------------------------------------------------------
# Repeated use — each call is an independent context
# ---------------------------------------------------------------------------

def test_conn_11_get_db_can_be_used_multiple_times_sequentially(monkeypatch):
    sessions = [_FakeSession(), _FakeSession()]
    calls = iter(sessions)
    monkeypatch.setattr(
        db_connection, "get_session_factory", lambda: (lambda: next(calls))
    )
    with db_connection.get_db() as db1:
        assert db1 is sessions[0]
    with db_connection.get_db() as db2:
        assert db2 is sessions[1]
    assert sessions[0].closed is True
    assert sessions[1].closed is True


# ---------------------------------------------------------------------------
# Remote-blocker follow-up (B1a): the PostgreSQL DBAPI driver required by
# connection.py's configured `postgresql://` URL must actually be installed
# and importable — psycopg2 was never declared as a project dependency
# anywhere (not core_engine/requirements.txt, not either Dockerfile), so
# SQLAlchemy's create_engine() raised ModuleNotFoundError the moment get_db()
# began reaching it for real (after the context-manager protocol fix).
# These tests require no network access and connect to no server — engine
# construction with NullPool/QueuePool is lazy and never dials out.
# ---------------------------------------------------------------------------

def test_conn_12_configured_url_uses_postgresql_scheme():
    """Sanity check: the dialect assertions below are only meaningful for postgresql://."""
    assert db_connection.DATABASE_URL.startswith("postgresql://"), (
        f"DATABASE_URL={db_connection.DATABASE_URL!r} — the psycopg2-binary "
        "dependency below is only required for the plain postgresql:// dialect"
    )


def test_conn_13_psycopg2_dbapi_is_importable():
    """
    The DBAPI driver SQLAlchemy's default postgresql:// dialect resolves to
    must be importable. This is what previously failed with
    ModuleNotFoundError: No module named 'psycopg2'.
    """
    import psycopg2  # noqa: F401 — import success is the assertion


def test_conn_14_create_engine_does_not_raise_module_not_found():
    """
    Constructing the real SQLAlchemy engine from the project's configured
    DATABASE_URL must not raise ModuleNotFoundError for the DBAPI driver.
    engine creation does not connect — no network access occurs.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    try:
        create_engine(db_connection.DATABASE_URL, poolclass=NullPool)
    except ModuleNotFoundError as e:
        pytest.fail(f"PostgreSQL DBAPI driver not installed: {e}")


def test_conn_15_get_engine_does_not_raise_module_not_found(monkeypatch):
    """
    The project's own get_engine() (not a hand-built engine) must also
    succeed — proves the fix is effective through the actual code path
    get_db() uses, not just a synthetic construction.
    """
    monkeypatch.setattr(db_connection, "_engine", None)
    try:
        db_connection.get_engine()
    except ModuleNotFoundError as e:
        pytest.fail(f"PostgreSQL DBAPI driver not installed: {e}")
    finally:
        monkeypatch.setattr(db_connection, "_engine", None)
