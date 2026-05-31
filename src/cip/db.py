"""Database layer — SQLAlchemy ORM (SQLite by default, Postgres-ready).

Swap to Postgres by setting CIP_DATABASE_URL=postgresql+psycopg://... — no code
change required. Tables: certificates, events (append-only), audit (append-only),
owner_suggestions (accuracy loop), dlq.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from cip.config import get_settings


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CertificateRow(Base):
    __tablename__ = "certificates"
    serial: Mapped[str] = mapped_column(String(128), primary_key=True)
    thumbprint: Mapped[str] = mapped_column(String(128), index=True)
    common_name: Mapped[str] = mapped_column(String(255), index=True)
    sans: Mapped[list] = mapped_column(JSON, default=list)
    ca: Mapped[str] = mapped_column(String(128))
    template: Mapped[str | None] = mapped_column(String(128), nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime)
    valid_to: Mapped[datetime] = mapped_column(DateTime, index=True)
    environment: Mapped[str] = mapped_column(String(16), index=True)
    criticality: Mapped[str] = mapped_column(String(16), index=True)
    application_ci: Mapped[str | None] = mapped_column(String(64), nullable=True)
    server_ci: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_group: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    escalation_path: Mapped[str | None] = mapped_column(String(128), nullable=True)
    renewal_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deploy_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    key_handling_policy: Mapped[str] = mapped_column(String(16), default="venafi")
    last_verified_endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_verified_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    tier: Mapped[str] = mapped_column(String(4), default="OK", index=True)
    owner_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    routing: Mapped[str] = mapped_column(String(20), default="STEWARD_TRIAGE", index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    jira_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class EventRow(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    serial: Mapped[str] = mapped_column(String(128), index=True)
    tier: Mapped[str | None] = mapped_column(String(4), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), index=True)
    actor: Mapped[str] = mapped_column(String(32), default="engine")
    detail: Mapped[str] = mapped_column(Text, default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class AuditRow(Base):
    """Append-only audit log — never updated or deleted."""

    __tablename__ = "audit"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(48))
    action: Mapped[str] = mapped_column(String(48), index=True)
    serial: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), default="ok")
    detail: Mapped[str] = mapped_column(Text, default="")


class OwnerSuggestionRow(Base):
    """Accuracy loop — AI suggestion vs human final answer."""

    __tablename__ = "owner_suggestions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    serial: Mapped[str] = mapped_column(String(128), index=True)
    suggested_owner: Mapped[str] = mapped_column(String(128))
    confidence: Mapped[float] = mapped_column(Float)
    human_final: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class DlqRow(Base):
    __tablename__ = "dlq"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32))
    serial: Mapped[str] = mapped_column(String(128), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


_engine = None
_SessionLocal: sessionmaker | None = None


def init_engine(database_url: str | None = None):
    global _engine, _SessionLocal
    url = database_url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, connect_args=connect_args, future=True)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def create_all():
    if _engine is None:
        init_engine()
    Base.metadata.create_all(_engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    if _SessionLocal is None:
        init_engine()
    assert _SessionLocal is not None
    s = _SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_session() -> Session:
    """FastAPI dependency-friendly session (caller must close)."""
    if _SessionLocal is None:
        init_engine()
    assert _SessionLocal is not None
    return _SessionLocal()
