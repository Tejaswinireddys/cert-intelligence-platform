"""APScheduler — daily scan + hourly auto-renewal fallback."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from cip.audit import get_logger
from cip.config import get_settings
from cip.engine import scanner

log = get_logger("scheduler")

_scheduler: BackgroundScheduler | None = None


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

    _scheduler.start()
    log.info("scheduler_started", cron=s.scan_cron)
    return _scheduler
