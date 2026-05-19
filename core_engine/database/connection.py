import os
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from .models import Base

# Database URL — override via DATABASE_URL env var
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://localhost:5432/expert_smart",
)

# Pool class — QueuePool for production (connection reuse),
# NullPool for development/testing (no overhead, simpler debugging).
# Override via ENVIRONMENT=production.
_ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
_POOL_CLASS = QueuePool if _ENVIRONMENT == "production" else NullPool

# Lazy singletons — created on first use, not at import time
_engine: Optional[Engine] = None
_SessionLocal = None


def get_engine() -> Engine:
    """Return (or create) the SQLAlchemy engine.

    Production (ENVIRONMENT=production):
        QueuePool — pool_size=5, max_overflow=10, pre-ping enabled.
        Keeps up to 15 live connections, health-checks before checkout.

    Development / test (default):
        NullPool — no persistent connections; safe for Flask/Waitress
        single-process and for tests that fork worker processes.
    """
    global _engine
    if _engine is None:
        kwargs: dict = {"echo": False, "pool_pre_ping": True}
        if _POOL_CLASS is QueuePool:
            kwargs["pool_size"]     = 5
            kwargs["max_overflow"]  = 10
        _engine = create_engine(DATABASE_URL, poolclass=_POOL_CLASS, **kwargs)
    return _engine


def get_session_factory():
    """Return (or create) the session factory bound to the current engine."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
    return _SessionLocal


# Convenience proxy — behaves like a callable session factory
class _SessionProxy:
    """Callable proxy that defers engine creation until first call."""
    def __call__(self):
        return get_session_factory()()

    def __bool__(self):
        return True


SessionLocal = _SessionProxy()


def init_db() -> None:
    """Create all tables defined in Base.metadata (idempotent)."""
    Base.metadata.create_all(bind=get_engine())


def drop_db() -> None:
    """Drop all tables (use only in tests / dev reset)."""
    Base.metadata.drop_all(bind=get_engine())


def get_db():
    """
    Yield a database session and guarantee it is closed on exit.

    Usage in Flask route handlers:

        with get_db() as db:
            db.add(record)
            db.commit()
    """
    db: Session = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def ping_db() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
