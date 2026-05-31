"""P1 escalation workflow — runs every 15 minutes.

If a P1 cert has been in 'open' or 'approved' state for longer than
CIP_P1_ESCALATION_MINUTES (default 30) without entering 'renewed', an
escalation Teams card is sent to the P1 webhook and the Jira ticket is
updated with an escalation note.

This complements the initial notify_agent message: if nobody acts within
the escalation window the system pages again and flags the ticket.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from cip.audit import audit, get_logger
from cip.config import get_settings
from cip.db import CertificateRow, EventRow, session_scope
from cip.integrations.jira import get_jira
from cip.integrations.teams import get_teams

log = get_logger("workflow.p1_escalation")


def _escalation_window_minutes() -> int:
    s = get_settings()
    return getattr(s, "p1_escalation_minutes", 30)


def _last_notified_at(serial: str) -> datetime | None:
    """Return the timestamp of the most recent 'notified' event for this cert."""
    with session_scope() as s:
        row = s.execute(
            select(EventRow)
            .where(EventRow.serial == serial)
            .where(EventRow.type == "notified")
            .order_by(EventRow.ts.desc())
        ).scalars().first()
        return row.ts.replace(tzinfo=timezone.utc) if row else None


def run() -> dict:
    """Escalate P1 certs that have not been renewed within the escalation window.

    Returns a summary dict with counts for monitoring / audit.
    """
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(minutes=_escalation_window_minutes())
    teams = get_teams()
    jira = get_jira()
    escalated: list[str] = []
    skipped: list[str] = []

    with session_scope() as s:
        rows = s.execute(
            select(CertificateRow)
            .where(CertificateRow.tier == "P1")
            .where(CertificateRow.status.in_(["open", "approved"]))
        ).scalars().all()
        candidates = list(rows)

    for row in candidates:
        last_notified = _last_notified_at(row.serial)
        if last_notified and last_notified > threshold:
            # Notified recently — still within window; do nothing.
            skipped.append(row.serial)
            continue

        # Beyond escalation window: page again and flag the Jira ticket.
        days_left = (row.valid_to.replace(tzinfo=timezone.utc) - now).days
        cert_ref = f"{row.common_name} · serial {row.serial[:12]}…"
        escalation_note = (
            f"ESCALATION: P1 cert {row.common_name} not renewed after "
            f"{_escalation_window_minutes()} min. {days_left}d left. "
            f"Owner: {row.owner_group or 'unknown'}. Env: {row.environment}."
        )

        try:
            teams.send(
                tier="P1",
                title=f"🚨 ESCALATION — P1 cert unactioned: {row.common_name}",
                text=escalation_note,
                action_label="Open Jira ticket",
                cert_ref=cert_ref,
            )
        except Exception as e:  # noqa: BLE001
            log.error("p1_escalation_teams_failed", serial=row.serial, error=str(e))

        if row.jira_key:
            try:
                jira.update_ticket(key=row.jira_key, tier="P1", note=escalation_note)
            except Exception as e:  # noqa: BLE001
                log.error("p1_escalation_jira_failed", serial=row.serial, error=str(e))

        audit(actor="workflow.p1_escalation", action="escalated", serial=row.serial,
              detail=f"no renewal after {_escalation_window_minutes()}min; paged again")
        log.info("p1_escalated", serial=row.serial, days_left=days_left,
                 owner=row.owner_group, env=row.environment)
        escalated.append(row.serial)

    log.info("p1_escalation_done", escalated=len(escalated), skipped=len(skipped))
    return {"escalated": len(escalated), "skipped": len(skipped), "serials": escalated}
