"""SQLAlchemy engine for the portal identity database (not Oracle)."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from api.auth.config import database_url

_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


def get_engine():
    global _engine
    if _engine is None:
        url = _normalize_database_url(database_url())
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, future=True, connect_args=connect_args)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    return _SessionLocal


@contextmanager
def temporary_engine():
    """Bind a fresh engine from the CURRENT env for the block, then restore the old one.

    The engine is built once per process, so a caller that points
    PORTAL_AUTH_DATABASE_URL at another database otherwise keeps writing to whichever
    one was opened first. Restoring rather than merely clearing matters: several
    callers use `sqlite:///:memory:`, and a cleared engine rebuilds that as an EMPTY
    database, silently discarding everything they had set up.
    """
    global _engine, _SessionLocal
    previous_engine, previous_factory = _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
    try:
        yield
    finally:
        if _engine is not None:
            _engine.dispose()
        _engine, _SessionLocal = previous_engine, previous_factory


def session_scope():
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
