"""Venafi native driver — load balancer / appliance / DNS-owned deploy.

Uses a platform-scoped credential; retains the rollback cert. Key is generated
on-device (appliance) or in Venafi; the driver installs the signed cert.
"""
from __future__ import annotations

from cip.audit import audit, get_logger
from cip.config import get_settings
from cip.execution.trigger import DeployRequest

log = get_logger("execution.venafi_driver")


def run(req: DeployRequest) -> dict:
    if not req.verify():
        audit(actor="execution", action="deploy_rejected", serial=req.serial,
              outcome="denied", detail="bad/expired signature")
        raise PermissionError("deploy request signature invalid or expired")

    s = get_settings()
    if s.mode == "MOCK":
        audit(actor="execution", action="venafi_driver_deploy", serial=req.serial,
              detail=f"native driver (mock) -> {req.target_endpoint} (rollback cert retained)")
        return {"deployed": True, "method": "venafi-driver", "rollback_retained": True,
                "endpoint": req.target_endpoint}
    # LIVE: invoke Venafi native provisioning driver (platform-scoped cred).
    raise NotImplementedError("LIVE venafi-driver provisioning configured per platform")  # pragma: no cover
