"""Webhook receivers — Jira approval transitions + Venafi events."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import select

from cip.audit import audit, get_logger
from cip.db import CertificateRow, session_scope
from cip.execution import saga
from cip.models import Certificate, Tier

router = APIRouter(prefix="/api/webhooks")
log = get_logger("api.webhooks")


@router.post("/jira")
async def jira_webhook(request: Request) -> dict:
    """Jira approval-transition webhook. When a prod cert ticket transitions to
    'Approved', kick the renew->deploy->verify saga."""
    payload = await request.json()
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})
    status = (fields.get("status") or {}).get("name", "")
    serial = (payload.get("changelog") or {}).get("serial") or payload.get("serial")
    audit(actor="jira", action="webhook_received", serial=serial,
          detail=f"status={status}")
    if status.lower() == "approved" and serial:
        saga.approve(serial, by="jira-webhook")
        result = saga.run_saga(serial)
        return {"received": True, "saga": result.get("saga")}
    return {"received": True, "status": status}


def _row_to_cert(row: CertificateRow) -> Certificate:
    return Certificate(
        serial=row.serial, thumbprint=row.thumbprint, common_name=row.common_name,
        sans=row.sans or [], ca=row.ca, template=row.template,
        valid_from=row.valid_from, valid_to=row.valid_to,
        environment=row.environment, criticality=row.criticality,
        application_ci=row.application_ci, server_ci=row.server_ci,
        owner_group=row.owner_group, escalation_path=row.escalation_path,
        renewal_method=row.renewal_method, deploy_method=row.deploy_method,
        key_handling_policy=row.key_handling_policy,
        last_verified_endpoint=row.last_verified_endpoint,
        last_verified_port=row.last_verified_port, risk_score=row.risk_score,
        tier=Tier(row.tier), owner_confidence=row.owner_confidence,
        status=row.status, jira_key=row.jira_key,
    )


def _handle_venafi_issued(*, serial_hint: str | None, thumbprint: str | None,
                          event_name: str) -> None:
    """Process Venafi cert-issuance events: sync CMDB when a deployed cert is confirmed.

    If the platform cert record is in 'renewed' or 'deployed' state, Venafi confirming
    issuance triggers a CMDB sync and (if already probe-verified) closes the Jira ticket.
    """
    from cip.agents import cmdb_agent

    with session_scope() as s:
        row: CertificateRow | None = None
        if serial_hint:
            row = s.get(CertificateRow, serial_hint)
        if row is None and thumbprint:
            row = s.execute(
                select(CertificateRow).where(CertificateRow.thumbprint == thumbprint)
            ).scalars().first()

        if row is None:
            log.warning("venafi_issued_unknown_cert", serial=serial_hint, thumbprint=thumbprint)
            return

        serial = row.serial
        if row.status not in ("renewed", "deployed"):
            log.info("venafi_issued_noop", serial=serial, status=row.status, event=event_name)
            return

        cert = _row_to_cert(row)

    # CMDB sync: link new cert serial to its server CI outside the session.
    cmdb_agent.sync_after_deploy(cert, new_serial=serial_hint or serial)
    audit(actor="venafi", action="issuance_confirmed", serial=serial,
          detail=f"event={event_name}; CMDB synced")
    log.info("venafi_issued_cmdb_sync", serial=serial, event=event_name)


@router.post("/venafi")
async def venafi_webhook(request: Request) -> dict:
    """Venafi event webhook: issuance complete, renewal confirmed, etc.

    Recognised eventName values:
      Certificate.Issued, Certificate.IssuedForVenafiCA, Certificate.Renewed
    → triggers CMDB sync when the platform cert record is in a deployed state.
    """
    payload = await request.json()
    event_name = payload.get("eventName", "unknown")
    audit(actor="venafi", action="webhook_received", detail=f"event={event_name}")

    issuance_events = {
        "Certificate.Issued",
        "Certificate.IssuedForVenafiCA",
        "Certificate.Renewed",
    }
    if event_name in issuance_events:
        serial_hint = payload.get("certificateSerial") or payload.get("serial")
        thumbprint = payload.get("thumbprint")
        try:
            _handle_venafi_issued(serial_hint=serial_hint, thumbprint=thumbprint,
                                  event_name=event_name)
        except Exception as e:  # noqa: BLE001
            log.error("venafi_issued_handler_failed", event=event_name, error=str(e))

    return {"received": True, "event": event_name}
