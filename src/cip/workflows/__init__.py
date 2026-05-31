"""In-platform workflow automation.

Each module is a scheduled job registered by cip.scheduler:
  p1_escalation  — every 15 min: escalate un-acted P1 prod certs to on-call
  weekly_digest  — Monday 08:00 UTC: P2/P3 digest per owner group via Teams
  orphan_reminder — daily 09:00 UTC: remind stewards about stale orphan queue
  sla_monitor    — every hour: alert if SLA compliance drops below threshold
"""
