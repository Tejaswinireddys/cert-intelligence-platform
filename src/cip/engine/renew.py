"""Deterministic renewal — plain Python, NO LLM.

Calls Venafi /certificaterequests. Idempotent by (serial + renewal_window).
A replayed renewal returns the same result; it can never trigger a second issue.
"""
from __future__ import annotations

from datetime import datetime

from cip.audit import audit
from cip.models.event import idempotency_key
from cip.venafi import get_venafi_client


def request_renewal(*, serial: str, valid_to_iso: str, key_handling_policy: str) -> dict:
    """Issue (or replay) a renewal request for a cert.

    The CSR / private key is generated at the workload or in Venafi per
    `key_handling_policy` (workload | venafi | hsm). This control-plane function
    never sees or returns private key material.
    """
    if key_handling_policy not in ("workload", "venafi", "hsm"):
        raise ValueError(f"invalid key_handling_policy: {key_handling_policy}")

    valid_to = datetime.fromisoformat(valid_to_iso)
    idem = idempotency_key(serial, valid_to)

    client = get_venafi_client()
    result = client.request_renewal(serial=serial, idempotency_key=idem)

    audit(actor="engine", action="renewal_requested", serial=serial,
          idempotency_key=idem, detail=f"status={result.get('status')} policy={key_handling_policy}")
    # Defensive: result must never carry key material.
    result.pop("privateKey", None)
    result.pop("keyMaterial", None)
    return result
