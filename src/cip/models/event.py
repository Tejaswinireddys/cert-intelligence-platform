"""Event envelope with idempotency key.

Every state-changing action is keyed so a replay cannot duplicate it.
A renewal is keyed by `cert_serial + renewal_window`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    SCANNED = "scanned"
    SCORED = "scored"
    TICKET_CREATED = "ticket_created"
    TICKET_UPDATED = "ticket_updated"
    NOTIFIED = "notified"
    APPROVED = "approved"
    BREAK_GLASS = "break_glass"
    RENEWAL_REQUESTED = "renewal_requested"
    RENEWED = "renewed"
    DEPLOYED = "deployed"
    VERIFIED = "verified"
    CLOSED = "closed"
    RENEWED_NOT_DEPLOYED = "renewed-not-deployed"
    ROLLBACK = "rollback"
    DLQ = "dlq"


def renewal_window(valid_to: datetime, *, now: Optional[datetime] = None) -> str:
    """ISO week label of the expiry — the renewal window bucket for idempotency."""
    vt = valid_to
    if vt.tzinfo is None:
        vt = vt.replace(tzinfo=timezone.utc)
    iso = vt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def idempotency_key(serial: str, valid_to: datetime) -> str:
    """`cert_serial + renewal_window` — the platform-wide idempotency key."""
    return f"{serial}:{renewal_window(valid_to)}"


class CertEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: EventType
    serial: str
    tier: Optional[str] = None
    idempotency_key: str
    actor: str = "engine"  # engine | jira_agent | renewal_agent | notify_agent | cmdb_agent | execution
    detail: str = ""
    attempts: int = 0
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
