"""Signed deploy-request issuer.

The control plane NEVER deploys. It issues a signed, scoped, time-boxed deploy
request that an execution-plane runner consumes. The request carries a cert
reference (serial) and target — never key material.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from cip.audit import audit, get_logger
from cip.config import get_secrets, get_settings

log = get_logger("execution.trigger")

DEPLOY_TTL_SECONDS = 900  # time-boxed: 15 minutes


def _signing_key() -> bytes:
    key = get_secrets().get(get_settings().tool_signing_key_path) or "dev-mock-tool-signing-key"
    return key.encode()


@dataclass
class DeployRequest:
    serial: str
    deploy_method: str  # venafi-driver | acme | ansible | manual
    target_endpoint: str
    target_port: int
    new_serial: str
    issued_at: float = field(default_factory=time.time)
    nonce: str = field(default_factory=lambda: uuid.uuid4().hex)
    signature: Optional[str] = None

    def _payload(self) -> str:
        return json.dumps(
            {
                "serial": self.serial,
                "deploy_method": self.deploy_method,
                "target_endpoint": self.target_endpoint,
                "target_port": self.target_port,
                "new_serial": self.new_serial,
                "issued_at": self.issued_at,
                "nonce": self.nonce,
            },
            sort_keys=True,
        )

    def sign(self) -> "DeployRequest":
        self.signature = hmac.new(_signing_key(), self._payload().encode(), hashlib.sha256).hexdigest()
        return self

    def verify(self) -> bool:
        if self.signature is None:
            return False
        expected = hmac.new(_signing_key(), self._payload().encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, self.signature):
            return False
        if time.time() - self.issued_at > DEPLOY_TTL_SECONDS:
            return False
        return True


def issue(*, serial: str, deploy_method: str, target_endpoint: str, target_port: int,
          new_serial: str) -> DeployRequest:
    req = DeployRequest(
        serial=serial, deploy_method=deploy_method, target_endpoint=target_endpoint,
        target_port=target_port, new_serial=new_serial,
    ).sign()
    audit(actor="execution", action="deploy_request_issued", serial=serial,
          detail=f"method={deploy_method} target={target_endpoint}:{target_port} nonce={req.nonce}")
    return req
