"""Weekly digest workflow — runs every Monday at 08:00 UTC.

Sends one Teams card per owner group containing:
  • P2 count (7-30d) and earliest expiry
  • P3 count (31-90d)
  • Current SLA compliance %

P1 certs are excluded: they are handled immediately by the P1 escalation
workflow and the initial notify_agent message. This digest is for planned
renewal scheduling — not emergency response.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select

from cip.audit import audit, get_logger
from cip.db import CertificateRow, session_scope
from cip.integrations.teams import get_teams

log = get_logger("workflow.weekly_digest")


def _sla_pct(rows: list[CertificateRow], now: datetime) -> float:
    actionable = [r for r in rows if r.tier != "OK"]
    if not actionable:
        return 100.0
    on_time = sum(
        1 for r in actionable
        if (r.valid_to.replace(tzinfo=timezone.utc) - now).days >= 0
    )
    return round(100 * on_time / len(actionable), 1)


def run() -> dict:
    """Build and dispatch the weekly P2/P3 digest to each owner group's Teams channel.

    Returns a count of digests sent and any groups skipped (no expiring certs).
    """
    now = datetime.now(timezone.utc)
    teams = get_teams()

    with session_scope() as s:
        all_rows = s.execute(select(CertificateRow)).scalars().all()

    overall_sla = _sla_pct(list(all_rows), now)

    # Group expiring (P2/P3) certs by owner group.
    by_group: dict[str, list[CertificateRow]] = defaultdict(list)
    for row in all_rows:
        if row.tier in ("P2", "P3") and row.status not in ("closed", "renewed"):
            group = row.owner_group or "Unassigned / Orphan"
            by_group[group].append(row)

    sent: list[str] = []
    skipped_empty: list[str] = []

    for group, group_rows in sorted(by_group.items()):
        p2 = [r for r in group_rows if r.tier == "P2"]
        p3 = [r for r in group_rows if r.tier == "P3"]

        if not p2 and not p3:
            skipped_empty.append(group)
            continue

        # Find earliest expiry in P2.
        earliest_days = None
        if p2:
            days_list = [
                (r.valid_to.replace(tzinfo=timezone.utc) - now).days for r in p2
            ]
            earliest_days = min(days_list)

        lines = []
        if p2:
            lines.append(f"**P2 (7–30d):** {len(p2)} cert(s)"
                         + (f" — earliest in {earliest_days}d" if earliest_days is not None else ""))
        if p3:
            lines.append(f"**P3 (31–90d):** {len(p3)} cert(s)")
        lines.append(f"Fleet SLA compliance: **{overall_sla}%**")

        cert_ref = f"{group} — {len(p2)} P2 + {len(p3)} P3 certs expiring"

        try:
            teams.send(
                tier="P3",
                title=f"📋 Weekly cert digest — {group}",
                text="\n\n".join(lines),
                action_label="View in dashboard",
                cert_ref=cert_ref,
            )
            sent.append(group)
            log.info("weekly_digest_sent", group=group, p2=len(p2), p3=len(p3))
        except Exception as e:  # noqa: BLE001
            log.error("weekly_digest_failed", group=group, error=str(e))

    audit(actor="workflow.weekly_digest", action="digest_sent",
          detail=f"groups={len(sent)} sla={overall_sla}%")
    log.info("weekly_digest_done", sent=len(sent), sla=overall_sla)
    return {"sent": len(sent), "groups": sent, "sla_pct": overall_sla}
