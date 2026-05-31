"""Webhook receivers — Jira approval transitions + Venafi events."""
from __future__ import annotations

from fastapi import APIRouter, Request

from cip.audit import audit, get_logger
from cip.execution import saga

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


@router.post("/venafi")
async def venafi_webhook(request: Request) -> dict:
    """Venafi event webhook (issuance complete, etc.)."""
    payload = await request.json()
    audit(actor="venafi", action="webhook_received",
          detail=f"event={payload.get('eventName', 'unknown')}")
    return {"received": True}
