"""SSL probe + rollback check.

Every deploy path ends here: confirm the new cert is live on
last_verified_endpoint:port. On failure -> keep the prior cert (rollback), flag
the Jira ticket `renewed-not-deployed`, do NOT close.
"""
from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass

from cip.audit import get_logger
from cip.config import get_settings

log = get_logger("execution.verify")


@dataclass
class VerifyResult:
    ok: bool
    endpoint: str
    port: int
    observed_serial: str | None = None
    detail: str = ""


def probe(*, endpoint: str, port: int, expected_serial: str | None = None,
          timeout: float = 5.0) -> VerifyResult:
    """SSL probe. MOCK mode simulates a successful probe matching expected_serial.

    LIVE mode opens a TLS connection and reads the served certificate's serial.
    """
    s = get_settings()
    if s.mode == "MOCK":
        return VerifyResult(ok=True, endpoint=endpoint, port=port,
                            observed_serial=expected_serial, detail="mock probe ok")
    try:  # pragma: no cover - needs network
        ctx = ssl.create_default_context()
        with socket.create_connection((endpoint, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=endpoint) as ssock:
                cert = ssock.getpeercert()
                observed = format(int(cert.get("serialNumber", "0"), 16), "X") if cert else None
        ok = expected_serial is None or (observed == expected_serial)
        return VerifyResult(ok=ok, endpoint=endpoint, port=port, observed_serial=observed,
                            detail="probe ok" if ok else "serial mismatch")
    except Exception as e:  # pragma: no cover
        return VerifyResult(ok=False, endpoint=endpoint, port=port, detail=f"probe failed: {e}")
