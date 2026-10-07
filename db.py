# db.py
"""
Database Connection and Session Management for ExamForge.
Configures SQLAlchemy with production-safe connection pooling for Supabase PostgreSQL on Render.
Ensures zero credential leakage in logs and provides a reusable session context manager.
"""

import os
import re
from contextlib import contextmanager
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool

# Load local .env if present
load_dotenv()

_ENGINE = None
_SESSION_FACTORY = None


def normalize_database_url(raw_url: str | None) -> str | None:
    """
    Normalizes database URL for SQLAlchemy compatibility:
    - Strips leading/trailing whitespace and quotes.
    - Converts legacy 'postgres://' to modern 'postgresql://' (or 'postgresql+psycopg2://').
    """
    if not raw_url:
        return None

    cleaned = str(raw_url).strip().strip('"').strip("'")
    if not cleaned:
        return None

    # Supabase / Render legacy prefix replacement
    if cleaned.startswith("postgres://"):
        cleaned = "postgresql+psycopg2://" + cleaned[len("postgres://"):]
    elif cleaned.startswith("postgresql://") and not cleaned.startswith("postgresql+"):
        cleaned = "postgresql+psycopg2://" + cleaned[len("postgresql://"):]

    return cleaned


def mask_database_url(url: str | None) -> str:
    """
    Returns a sanitized database URL with password masked for safe logging.
    Guarantees no passwords or credentials are exposed in logs.
    """
    if not url:
        return "None"

    try:
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(f":{parsed.password}@", ":****@")
            masked = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            return masked
        return url
    except Exception:
        # Fallback regex masking if URL parsing fails
        return re.sub(r":([^/@:]+)@", r":****@", str(url))


def get_database_url() -> str | None:
    """Retrieves and normalizes DATABASE_URL from environment variables."""
    raw = os.getenv("DATABASE_URL")
    return normalize_database_url(raw)


def is_database_configured() -> bool:
    """Returns True if DATABASE_URL environment variable is present and non-empty."""
    return get_database_url() is not None


def get_engine():
    """
    Initializes and returns a singleton SQLAlchemy engine.
    Applies connection pooling tuned specifically for Render + Supabase limits:
    - pool_size=5: Maintains a conservative number of connections per worker.
    - max_overflow=5: Allows temporary bursting up to 10 connections.
    - pool_timeout=30: Waits up to 30s before timing out on pool exhaustion.
    - pool_recycle=1800: Refreshes idle connections after 30 minutes to prevent disconnects.
    - pool_pre_ping=True: Liveness check to drop stale connections before query execution.
    """
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    url = get_database_url()
    if not url:
        return None

    _ENGINE = create_engine(
        url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False
    )
    return _ENGINE


def get_session_factory():
    """Returns a thread-safe scoped sessionmaker bound to the engine."""
    global _SESSION_FACTORY
    if _SESSION_FACTORY is not None:
        return _SESSION_FACTORY

    engine = get_engine()
    if engine is None:
        return None

    _SESSION_FACTORY = scoped_session(
        sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False
        )
    )
    return _SESSION_FACTORY


@contextmanager
def get_db_session():
    """
    Context manager providing a transactional database session:
    - Automatically commits on success.
    - Automatically rolls back on exception.
    - Always closes/returns connection to the pool.
    """
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("DATABASE_URL is not configured. Cannot establish database session.")

    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_db_connection() -> tuple[bool, str]:
    """
    Safely tests database connectivity using 'SELECT 1'.
    Returns (True, message) on success or (False, error_summary) on failure.
    CRITICAL: Never exposes passwords or unmasked credentials in output.
    """
    url = get_database_url()
    if not url:
        return False, "DATABASE_URL environment variable is not set."

    masked = mask_database_url(url)
    engine = get_engine()
    if engine is None:
        return False, "Could not initialize SQLAlchemy engine."

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            if result == 1:
                return True, f"PostgreSQL connection successful to: {masked}"
            return False, f"Unexpected query response ({result}) from: {masked}"
    except Exception as exc:
        err_msg = str(exc)
        # Strip any accidental passwords from exception string
        if url:
            parsed = urlparse(url)
            if parsed.password:
                err_msg = err_msg.replace(parsed.password, "****")
        return False, f"Connection failed: {err_msg}"


def create_all_tables():
    """
    Explicitly creates all application tables in the database if they do not exist.
    IMPORTANT: This is NOT called automatically on application startup.
    Must be executed deliberately via migration scripts or management commands.
    """
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured. Cannot create tables.")

    from models import Base
    Base.metadata.create_all(bind=engine)
