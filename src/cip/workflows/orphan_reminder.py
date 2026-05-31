"""Orphan reminder workflow — runs daily at 09:00 UTC.

Certs in STEWARD_TRIAGE (owner confidence < 0.50) sit in the orphan queue
until a steward manually assigns an owner. Without reminders, P2/P3 orphans
can drift past expiry unnoticed.

This workflow:
  1. Counts orphan certs by tier and days-in-queue bracket.
  2. Sends a single summary Teams card to the steward team channel (P3 tier).
  3. For any P1 orphan (dangerous: expiring in < 7d with no owner), sends an
     immediate P1 card and raises the audit severity.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from cip.audit import audit, get_logger
from cip.db import CertificateRow, EventRow, session_scope
from cip.integrations.teams import get_teams

log = get_logger("workflow.orphan_reminder")

# Remind about orphans older than this many hours to avoid noise on fresh scans.
_STALE_HOURS = 4


def _first_seen_at(serial: str) -> datetime | None:
    with session_scope() as s:
        row = s.execute(
            select(EventRow)
            .where(EventRow.serial == serial)
            .where(EventRow.type == "scanned")
            .order_by(EventRow.ts.asc())
        ).scalars().first()
        return row.ts.replace(tzinfo=timezone.utc) if row else None


def run() -> dict:
    """Send orphan-queue reminder to the steward channel.

    Returns counts broken down by tier.
    """
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(hours=_STALE_HOURS)
    teams = get_teams()

    with session_scope() as s:
        rows = s.execute(
            select(CertificateRow)
            .where(CertificateRow.routing == "STEWARD_TRIAGE")
            .where(CertificateRow.status.not_in(["closed"]))
        ).scalars().all()
        orphans = list(rows)

    # Filter to orphans that have been sitting for > _STALE_HOURS.
    stale: list[CertificateRow] = []
    for row in orphans:
        first_seen = _first_seen_at(row.serial)
        if first_seen is None or first_seen < stale_cutoff:
            stale.append(row)

    if not stale:
        log.info("orphan_reminder_none", total=len(orphans))
        return {"p1": 0, "p2": 0, "p3": 0, "total": 0}

    p1_orphans = [r for r in stale if r.tier == "P1"]
    p2_orphans = [r for r in stale if r.tier == "P2"]
    p3_orphans = [r for r in stale if r.tier == "P3"]

    # P1 orphans are critical: expiring soon with no known owner.
    for row in p1_orphans:
        days_left = (row.valid_to.replace(tzinfo=timezone.utc) - now).days
        try:
            teams.send(
                tier="P1",
                title=f"🚨 P1 ORPHAN — {row.common_name} has no owner ({days_left}d left)",
                text=(
                    f"Certificate **{row.common_name}** (serial `{row.serial[:12]}…`) "
                    f"is expiring in **{days_left} day(s)** and has no confirmed owner "
                    f"(confidence: {row.owner_confidence:.0%}). "
                    f"Please assign an owner immediately in the certificate dashboard."
                ),
                action_label="Assign owner now",
                cert_ref=f"{row.common_name} · {row.environment} · {days_left}d",
            )
        except Exception as e:  # noqa: BLE001
            log.error("orphan_p1_teams_failed", serial=row.serial, error=str(e))
        audit(actor="workflow.orphan_reminder", action="p1_orphan_alert", serial=row.serial,
              outcome="warning", detail=f"{days_left}d left, no owner")

    # Summary card for all stale orphans.
    lines: list[str] = []
    if p1_orphans:
        lines.append(f"🔴 **P1 (critical):** {len(p1_orphans)} — assign immediately")
    if p2_orphans:
        lines.append(f"🟡 **P2:** {len(p2_orphans)} cert(s) expiring 7–30d")
    if p3_orphans:
        lines.append(f"🟢 **P3:** {len(p3_orphans)} cert(s) expiring 31–90d")
    lines.append(f"\nTotal stale orphans: **{len(stale)}**")
    lines.append("Open the Orphan Queue in the dashboard to assign owners.")

    try:
        teams.send(
            tier="P3",
            title=f"👻 Orphan queue reminder — {len(stale)} cert(s) need an owner",
            text="\n\n".join(lines),
            action_label="Open orphan queue",
            cert_ref=f"{len(stale)} certs unassigned",
        )
    except Exception as e:  # noqa: BLE001
        log.error("orphan_reminder_summary_failed", error=str(e))

    audit(actor="workflow.orphan_reminder", action="reminder_sent",
          detail=f"stale={len(stale)} p1={len(p1_orphans)} p2={len(p2_orphans)} p3={len(p3_orphans)}")
    log.info("orphan_reminder_done", total=len(stale), p1=len(p1_orphans),
             p2=len(p2_orphans), p3=len(p3_orphans))
    return {"p1": len(p1_orphans), "p2": len(p2_orphans), "p3": len(p3_orphans),
            "total": len(stale)}
