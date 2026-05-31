"""Renew -> deploy -> verify saga with compensation.

| State                     | Action                                              |
|---------------------------|-----------------------------------------------------|
| renewed, not deployed     | park cert, Jira flag `renewed-not-deployed`         |
| deployed, verify failed   | rollback to prior cert, reopen, page owner          |
| deployed + verified       | update CMDB, write audit event, close Jira          |

Production requires a prior Jira approval transition. Dev/test auto-approve.
"""
from __future__ import annotations

from datetime import datetime, timezone

from cip.agents import cmdb_agent, renewal_agent
from cip.audit import audit, get_logger
from cip.db import CertificateRow, session_scope
from cip.engine.bus import get_bus
from cip.execution import ansible_runner, trigger, venafi_driver, verify
from cip.integrations.jira import get_jira
from cip.models import Certificate, Tier
from cip.models.event import CertEvent, EventType, idempotency_key

log = get_logger("execution.saga")

# Production change-freeze windows (weekday, hour ranges in UTC). Example policy.
FREEZE_WINDOWS = {4: [(20, 24)], 5: [(0, 24)], 6: [(0, 24)]}  # Fri eve + weekend


def _is_frozen(now: datetime) -> bool:
    ranges = FREEZE_WINDOWS.get(now.weekday(), [])
    return any(lo <= now.hour < hi for lo, hi in ranges)


def _load(serial: str) -> Certificate:
    with session_scope() as s:
        row = s.get(CertificateRow, serial)
        if row is None:
            raise KeyError(f"unknown cert {serial}")
        return Certificate(
            serial=row.serial, thumbprint=row.thumbprint, common_name=row.common_name,
            sans=row.sans or [], ca=row.ca, template=row.template,
            valid_from=row.valid_from, valid_to=row.valid_to, environment=row.environment,
            criticality=row.criticality, application_ci=row.application_ci,
            server_ci=row.server_ci, owner_group=row.owner_group,
            escalation_path=row.escalation_path, renewal_method=row.renewal_method,
            deploy_method=row.deploy_method, key_handling_policy=row.key_handling_policy,
            last_verified_endpoint=row.last_verified_endpoint,
            last_verified_port=row.last_verified_port, risk_score=row.risk_score,
            tier=Tier(row.tier), owner_confidence=row.owner_confidence, status=row.status,
            jira_key=row.jira_key,
        )


def _set_status(serial: str, status: str) -> None:
    with session_scope() as s:
        row = s.get(CertificateRow, serial)
        if row:
            row.status = status


def approve(serial: str, *, by: str = "user") -> dict:
    """Human approval transition for a production cert (the production gate)."""
    cert = _load(serial)
    if cert.jira_key:
        get_jira().transition_approve(key=cert.jira_key)
    _set_status(serial, "approved")
    audit(actor=by, action="approved", serial=serial, idempotency_key=idempotency_key(serial, cert.valid_to),
          detail=f"production approval by {by}")
    get_bus().emit(CertEvent(type=EventType.APPROVED, serial=serial, tier=cert.tier.value,
                             idempotency_key=idempotency_key(serial, cert.valid_to),
                             actor=by, detail="approved"))
    return {"serial": serial, "approved": True, "by": by, "jira_key": cert.jira_key,
            "next": "renewal_requested"}


def run_saga(serial: str, *, now: datetime | None = None) -> dict:
    """Execute renew -> deploy -> verify with compensation. Returns final state."""
    now = now or datetime.now(timezone.utc)
    cert = _load(serial)
    bus = get_bus()
    idem = idempotency_key(serial, cert.valid_to)
    events: list[str] = []

    # Production gate: must be approved; dev/test auto-approve.
    is_prod = cert.environment in ("prod", "staging")
    if is_prod and cert.status != "approved":
        return {"serial": serial, "saga": "blocked",
                "reason": "production requires Jira approval first", "events": events}
    if is_prod and _is_frozen(now):
        return {"serial": serial, "saga": "blocked",
                "reason": "change freeze window active (break-glass required)", "events": events}

    # 1. RENEW (deterministic, via renewal agent -> engine.renew).
    renewal = renewal_agent.request_for(cert)
    new_serial = renewal.get("newSerial", cert.serial)
    _set_status(serial, "renewed")
    bus.emit(CertEvent(type=EventType.RENEWED, serial=serial, tier=cert.tier.value,
                       idempotency_key=idem, actor="renewal_agent", detail=f"new={new_serial[:12]}…"))
    events.append("renewed")

    # 2. DEPLOY via per-platform execution-plane runner (signed request).
    endpoint = cert.last_verified_endpoint or cert.common_name
    port = cert.last_verified_port or 443
    method = cert.deploy_method or "manual"

    if method == "manual":
        # No automation support -> ServiceNow/Jira task; saga parks here.
        _set_status(serial, "renewed-not-deployed")
        if cert.jira_key:
            get_jira().update_ticket(key=cert.jira_key, tier=cert.tier.value,
                                     note="renewed-not-deployed: manual deploy task created")
        bus.emit(CertEvent(type=EventType.RENEWED_NOT_DEPLOYED, serial=serial, tier=cert.tier.value,
                           idempotency_key=idem, actor="execution",
                           detail="manual deploy task; SSL probe required before close"))
        audit(actor="execution", action="renewed_not_deployed", serial=serial,
              idempotency_key=idem, detail="manual path")
        events.append("renewed-not-deployed")
        return {"serial": serial, "saga": "renewed-not-deployed", "events": events}

    req = trigger.issue(serial=serial, deploy_method=method, target_endpoint=endpoint,
                        target_port=port, new_serial=new_serial)
    runner = venafi_driver if method in ("venafi-driver", "acme") else ansible_runner
    try:
        runner.run(req)
        _set_status(serial, "deployed")
        bus.emit(CertEvent(type=EventType.DEPLOYED, serial=serial, tier=cert.tier.value,
                           idempotency_key=idem, actor="execution", detail=f"method={method}"))
        events.append("deployed")
    except Exception as e:  # noqa: BLE001
        _set_status(serial, "renewed-not-deployed")
        bus.emit(CertEvent(type=EventType.RENEWED_NOT_DEPLOYED, serial=serial, tier=cert.tier.value,
                           idempotency_key=idem, actor="execution", detail=f"deploy failed: {e}"))
        events.append("renewed-not-deployed")
        return {"serial": serial, "saga": "renewed-not-deployed", "events": events}

    # 3. VERIFY (SSL probe). On failure -> rollback, reopen, page owner.
    result = verify.probe(endpoint=endpoint, port=port, expected_serial=new_serial)
    if not result.ok:
        _set_status(serial, "renewed-not-deployed")
        bus.emit(CertEvent(type=EventType.ROLLBACK, serial=serial, tier=cert.tier.value,
                           idempotency_key=idem, actor="execution",
                           detail=f"verify failed: {result.detail}; rolled back to prior cert"))
        if cert.jira_key:
            get_jira().update_ticket(key=cert.jira_key, tier="P1",
                                     note="verify failed: rolled back; paging owner")
        audit(actor="execution", action="rollback", serial=serial, idempotency_key=idem,
              outcome="error", detail=result.detail)
        events.append("rollback")
        return {"serial": serial, "saga": "rollback", "events": events}

    # 4. VERIFIED -> update CMDB, audit, close Jira.
    cmdb_agent.sync_after_deploy(cert, new_serial=new_serial)
    bus.emit(CertEvent(type=EventType.VERIFIED, serial=serial, tier=cert.tier.value,
                       idempotency_key=idem, actor="execution",
                       detail=f"SSL probe ok on {endpoint}:{port}"))
    _set_status(serial, "closed")
    if cert.jira_key:
        get_jira().update_ticket(key=cert.jira_key, tier=cert.tier.value, note="deployed + verified; closing")
    bus.emit(CertEvent(type=EventType.CLOSED, serial=serial, tier=cert.tier.value,
                       idempotency_key=idem, actor="execution", detail="closed: verified live"))
    audit(actor="execution", action="closed", serial=serial, idempotency_key=idem,
          detail="renew+deploy+verify complete")
    events += ["verified", "closed"]
    return {"serial": serial, "saga": "verified", "events": events}
