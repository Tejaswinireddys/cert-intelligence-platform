"""Dedup / idempotency guard — PURE-ish logic, unit-tested to 100%.

    idempotency_key = f"{cert.serial}:{renewal_window}"

Before creating a Jira ticket or queuing a renewal, check the key. If it exists
-> update the existing ticket (tier change) instead of creating a new one.

The decision logic is a pure function (`decide`) so it can be exhaustively
unit-tested. The persistence-backed `guard` wraps it.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from cip.models.event import idempotency_key  # re-exported for callers

__all__ = ["idempotency_key", "DedupAction", "DedupDecision", "decide", "DedupGuard"]


class DedupAction(str, Enum):
    CREATE = "create"  # no prior record for this key -> create new ticket/event
    UPDATE = "update"  # prior record exists but tier changed -> update existing
    SKIP = "skip"  # prior record exists, tier unchanged -> no-op (replay)


@dataclass(frozen=True)
class DedupDecision:
    action: DedupAction
    reason: str
    existing_jira_key: Optional[str] = None


def decide(
    *,
    existing_tier: Optional[str],
    new_tier: str,
    existing_jira_key: Optional[str] = None,
) -> DedupDecision:
    """Pure decision: given the prior known tier for an idempotency key and the
    newly computed tier, decide whether to CREATE, UPDATE, or SKIP.

    - existing_tier is None  -> never seen -> CREATE
    - existing_tier == new   -> replay/no change -> SKIP
    - existing_tier != new   -> escalation/de-escalation -> UPDATE
    """
    if existing_tier is None:
        return DedupDecision(DedupAction.CREATE, "no prior record for idempotency key")
    if existing_tier == new_tier:
        return DedupDecision(
            DedupAction.SKIP, "tier unchanged; replay suppressed", existing_jira_key
        )
    return DedupDecision(
        DedupAction.UPDATE,
        f"tier changed {existing_tier} -> {new_tier}",
        existing_jira_key,
    )


class DedupGuard:
    """Persistence-backed wrapper around `decide`.

    Looks up the most recent known tier for an idempotency key from the events
    table and returns the dedup decision.
    """

    def __init__(self, session_factory=None):
        self._sf = session_factory

    def _lookup(self, idem_key: str) -> tuple[Optional[str], Optional[str]]:
        from sqlalchemy import select

        from cip.db import CertificateRow, EventRow, session_scope

        sf = self._sf or session_scope
        with sf() as s:
            row = (
                s.execute(
                    select(EventRow)
                    .where(EventRow.idempotency_key == idem_key)
                    .where(EventRow.type == "ticket_created")
                    .order_by(EventRow.ts.desc())
                )
                .scalars()
                .first()
            )
            if row is None:
                return None, None
            cert = s.get(CertificateRow, row.serial)
            jira_key = cert.jira_key if cert else None
            return (row.tier, jira_key)

    def check(self, *, idem_key: str, new_tier: str) -> DedupDecision:
        existing_tier, jira_key = self._lookup(idem_key)
        return decide(
            existing_tier=existing_tier, new_tier=new_tier, existing_jira_key=jira_key
        )
