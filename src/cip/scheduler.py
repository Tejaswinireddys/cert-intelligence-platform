"""APScheduler — deterministic daily expiry scan."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from cip.audit import get_logger
from cip.config import get_settings
from cip.engine import scanner

log = get_logger("scheduler")

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    s = get_settings()
    _scheduler = BackgroundScheduler(timezone="UTC")
    minute, hour, dom, month, dow = s.scan_cron.split()
    _scheduler.add_job(
        lambda: scanner.scan(),
        CronTrigger(minute=minute, hour=hour, day=dom, month=month, day_of_week=dow),
        id="daily_scan", replace_existing=True,
    )
    _scheduler.start()
    log.info("scheduler_started", cron=s.scan_cron)
    return _scheduler
