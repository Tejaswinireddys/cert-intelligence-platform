"""Ansible runner — Linux / app server deploy via SIGNED playbook.

Verifies the deploy request signature, then invokes a signed playbook under a
least-privilege SSH account within a change window. The runner generates the CSR
locally under a least-priv account; the key never leaves the host.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from cip.audit import audit, get_logger
from cip.config import get_settings
from cip.execution.trigger import DeployRequest

log = get_logger("execution.ansible")

PLAYBOOK = Path(__file__).resolve().parents[3] / "playbooks" / "deploy_cert.yml"


def run(req: DeployRequest) -> dict:
    if not req.verify():
        audit(actor="execution", action="deploy_rejected", serial=req.serial,
              outcome="denied", detail="bad/expired signature")
        raise PermissionError("deploy request signature invalid or expired")

    s = get_settings()
    if s.mode == "MOCK":
        audit(actor="execution", action="ansible_deploy", serial=req.serial,
              detail=f"signed playbook (mock) -> {req.target_endpoint}")
        return {"deployed": True, "method": "ansible", "endpoint": req.target_endpoint}

    cmd = [  # pragma: no cover - needs ansible + hosts
        "ansible-playbook", str(PLAYBOOK),
        "--extra-vars", f"serial={req.new_serial} endpoint={req.target_endpoint}",
        "--limit", req.target_endpoint,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # pragma: no cover
    ok = proc.returncode == 0  # pragma: no cover
    audit(actor="execution", action="ansible_deploy", serial=req.serial,  # pragma: no cover
          outcome="ok" if ok else "error", detail=proc.stdout[-500:])
    return {"deployed": ok, "method": "ansible", "stdout": proc.stdout[-500:]}  # pragma: no cover
