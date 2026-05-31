"""SLA monitor workflow — runs every hour.

Computes current SLA compliance (% of actionable certs not expired) and
compares it to the configured threshold (CIP_SLA_ALERT_THRESHOLD, default 90%).

When compliance drops below the threshold:
  • A P2 Teams card is sent to the steward channel.
  • An audit event is written with outcome='warning'.

When compliance recovers above the threshold after a prior alert:
  • A recovery Teams card is sent.
  • An audit event is written with outcome='ok'.

State is tracked via the audit table to avoid sending duplicate alerts every
hour while the SLA is continuously below threshold.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from cip.audit import audit, get_logger
from cip.db import AuditRow, CertificateRow, session_scope
from cip.integrations.teams import get_teams

log = get_logger("workflow.sla_monitor")

_DEFAULT_THRESHOLD = 90.0
_ALERT_COOLDOWN_HOURS = 4  # don't re-alert more than once per 4h


def _threshold() -> float:
    from cip.config import get_settings

    s = get_settings()
    return getattr(s, "sla_alert_threshold", _DEFAULT_THRESHOLD)


def _last_alert_at() -> datetime | None:
    """Return the timestamp of the most recent SLA alert audit entry."""
    with session_scope() as s:
        row = s.execute(
            select(AuditRow)
            .where(AuditRow.actor == "workflow.sla_monitor")
            .where(AuditRow.action == "sla_alert")
            .order_by(AuditRow.ts.desc())
        ).scalars().first()
        return row.ts.replace(tzinfo=timezone.utc) if row else None


def _compute_sla(now: datetime) -> tuple[float, int, int]:
    """Return (sla_pct, actionable_count, expired_count)."""
    with session_scope() as s:
        rows = s.execute(select(CertificateRow)).scalars().all()
    actionable = [r for r in rows if r.tier != "OK"]
    expired = [
        r for r in actionable
        if (r.valid_to.replace(tzinfo=timezone.utc) - now).days < 0
    ]
    if not actionable:
        return 100.0, 0, 0
    sla = round(100 * (len(actionable) - len(expired)) / len(actionable), 1)
    return sla, len(actionable), len(expired)


def run() -> dict:
    """Check SLA compliance and fire an alert card if below threshold.

    Returns a dict with current sla_pct, threshold, and action taken.
    """
    now = datetime.now(timezone.utc)
    threshold = _threshold()
    sla_pct, actionable, expired = _compute_sla(now)

    if sla_pct >= threshold:
        log.info("sla_ok", sla_pct=sla_pct, threshold=threshold)
        return {"sla_pct": sla_pct, "threshold": threshold, "action": "none"}

    # SLA is below threshold.
    last_alert = _last_alert_at()
    cooldown_cutoff = now - timedelta(hours=_ALERT_COOLDOWN_HOURS)
    if last_alert and last_alert > cooldown_cutoff:
        log.info("sla_alert_suppressed", sla_pct=sla_pct, last_alert=last_alert.isoformat())
        return {"sla_pct": sla_pct, "threshold": threshold, "action": "suppressed"}

    # Send alert.
    drop = round(threshold - sla_pct, 1)
    text = (
        f"Fleet SLA compliance has dropped to **{sla_pct}%** "
        f"(threshold: {threshold}%, drop: {drop}pp).\n\n"
        f"**{expired}** of **{actionable}** actionable cert(s) are expired or past due.\n\n"
        f"Check the dashboard for details and renew or assign owners as needed."
    )
    teams = get_teams()
    try:
        teams.send(
            tier="P2",
            title=f"⚠️ SLA compliance below threshold: {sla_pct}% (target ≥{threshold}%)",
            text=text,
            action_label="Open dashboard",
            cert_ref=f"{expired} cert(s) expired of {actionable} actionable",
        )
    except Exception as e:  # noqa: BLE001
        log.error("sla_alert_teams_failed", sla_pct=sla_pct, error=str(e))

    audit(actor="workflow.sla_monitor", action="sla_alert", outcome="warning",
          detail=f"sla={sla_pct}% threshold={threshold}% expired={expired}/{actionable}")
    log.warning("sla_alert_fired", sla_pct=sla_pct, threshold=threshold,
                expired=expired, actionable=actionable)
    return {"sla_pct": sla_pct, "threshold": threshold, "action": "alerted",
            "expired": expired, "actionable": actionable}
