"""APScheduler — all platform scheduled jobs.

Jobs registered:
  daily_scan          — configurable cron (default 06:00 UTC): scan + score + route + ticket
  auto_renew_pending  — every hour at :45: run saga for open AUTO dev/test certs
  p1_escalation       — every 15 min: page on-call if P1 certs are unactioned
  weekly_digest       — Monday 08:00 UTC: P2/P3 digest per owner group via Teams
  orphan_reminder     — daily 09:00 UTC: remind stewards about stale orphan queue
  sla_monitor         — every hour at :00: alert if SLA compliance < threshold
"""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from cip.audit import get_logger
from cip.config import get_settings
from cip.engine import scanner

log = get_logger("scheduler")

_scheduler: BackgroundScheduler | None = None


def _run_workflow(name: str):
    """Return a zero-arg callable that imports and runs a workflow module by name.

    Each workflow is imported lazily so scheduler startup is fast even if a
    workflow module has an import-time issue — the error surfaces only when that
    job fires, and is caught + logged rather than crashing the scheduler.
    """
    def _job():
        try:
            import importlib
            module = importlib.import_module(f"cip.workflows.{name}")
            result = module.run()
            log.info(f"workflow_{name}_done", **{k: v for k, v in (result or {}).items()
                                                  if isinstance(v, (int, float, str, bool))})
        except Exception as e:  # noqa: BLE001
            log.error(f"workflow_{name}_error", error=str(e))

    _job.__name__ = f"workflow_{name}"
    return _job


def _auto_renew_pending() -> None:
    """Hourly fallback: run saga for any AUTO dev/test certs still open.

    Catches certs missed by the inline auto-renew in scanner (e.g. if the scan
    ran before the cert was created, or a previous saga attempt failed).
    Only acts on P1/P2/P3 (not OK) certs to avoid unnecessary operations.
    """
    from sqlalchemy import select

    from cip.db import CertificateRow, session_scope
    from cip.execution import saga

    with session_scope() as s:
        rows = s.execute(
            select(CertificateRow)
            .where(CertificateRow.routing == "AUTO")
            .where(CertificateRow.status == "open")
            .where(CertificateRow.environment.in_(["dev", "test"]))
            .where(CertificateRow.tier.in_(["P1", "P2", "P3"]))
        ).scalars().all()
        serials = [r.serial for r in rows]

    log.info("auto_renew_pending_start", count=len(serials))
    for serial in serials:
        try:
            result = saga.run_saga(serial)
            log.info("auto_renew_pending_result", serial=serial, saga=result.get("saga"))
        except Exception as e:  # noqa: BLE001
            log.error("auto_renew_pending_failed", serial=serial, error=str(e))


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    s = get_settings()
    _scheduler = BackgroundScheduler(timezone="UTC")
    minute, hour, dom, month, dow = s.scan_cron.split()

    # Job 1: daily full scan (detect, score, route, ticket, notify).
    _scheduler.add_job(
        lambda: scanner.scan(),
        CronTrigger(minute=minute, hour=hour, day=dom, month=month, day_of_week=dow),
        id="daily_scan", replace_existing=True,
    )

    # Job 2: hourly auto-renewal fallback for open AUTO dev/test certs.
    # Runs at :45 past every hour to avoid colliding with common :00/:30 scan times.
    _scheduler.add_job(
        _auto_renew_pending,
        CronTrigger(minute="45"),
        id="auto_renew_pending", replace_existing=True,
    )

    # Job 3: P1 escalation — every 15 minutes.
    _scheduler.add_job(
        _run_workflow("p1_escalation"),
        CronTrigger(minute="*/15"),
        id="p1_escalation", replace_existing=True,
    )

    # Job 4: Weekly P2/P3 digest — Monday at 08:00 UTC.
    _scheduler.add_job(
        _run_workflow("weekly_digest"),
        CronTrigger(day_of_week="mon", hour="8", minute="0"),
        id="weekly_digest", replace_existing=True,
    )

    # Job 5: Orphan reminder — daily at 09:00 UTC.
    _scheduler.add_job(
        _run_workflow("orphan_reminder"),
        CronTrigger(hour="9", minute="0"),
        id="orphan_reminder", replace_existing=True,
    )

    # Job 6: SLA monitor — every hour at :00.
    _scheduler.add_job(
        _run_workflow("sla_monitor"),
        CronTrigger(minute="0"),
        id="sla_monitor", replace_existing=True,
    )

    _scheduler.start()
    log.info("scheduler_started", cron=s.scan_cron,
             jobs=["daily_scan", "auto_renew_pending", "p1_escalation",
                   "weekly_digest", "orphan_reminder", "sla_monitor"])
    return _scheduler
