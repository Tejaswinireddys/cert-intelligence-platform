"""Venafi client — Layer 0.

Supports TPP (OAuth token) and VCP/SaaS (API key). In MOCK mode it serves
from a simulated inventory so the whole platform runs end-to-end without a real
Venafi tenant. In LIVE mode it calls the Venafi REST API (vcert-compatible).

NOTE: This client returns certificate METADATA only. It never returns private
key material to the control plane.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Optional

import httpx

from cip.audit import get_logger
from cip.config import Settings, get_secrets, get_settings
from cip.venafi import mock as mock_inventory

log = get_logger("venafi")


class VenafiClient:
    def __init__(self, settings: Settings):
        self.s = settings
        self.secrets = get_secrets()
        self._http: Optional[httpx.Client] = None

    # --- auth -------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        if self.s.venafi_platform == "VCP":
            key = self.secrets.get(self.s.venafi_apikey_path, required=True)
            return {"tppl-api-key": key}
        token = self.secrets.get(self.s.venafi_tpp_token_path, required=True)
        return {"Authorization": f"Bearer {token}"}

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                base_url=self.s.venafi_base_url, headers=self._headers(), timeout=30.0
            )
        return self._http

    # --- search -----------------------------------------------------------
    def search_expiring(self, within_days: int) -> list[dict]:
        """certificatesearch filtered by validityEnd within `within_days`."""
        if self.s.mode == "MOCK":
            return mock_inventory.search_expiring(within_days)
        # LIVE: VCP certificatesearch
        body = {
            "expression": {
                "operands": [
                    {
                        "field": "validityEnd",
                        "operator": "LTE",
                        "value": _iso_in_days(within_days),
                    }
                ]
            }
        }
        resp = self.http.post("/outagedetection/v1/certificatesearch", json=body)
        resp.raise_for_status()
        return resp.json().get("certificates", [])

    def search_all(self) -> list[dict]:
        """Full inventory (for tracking healthy certs too). MOCK only convenience;
        LIVE callers should page certificatesearch without a validityEnd filter."""
        if self.s.mode == "MOCK":
            return mock_inventory.search_all()
        resp = self.http.post("/outagedetection/v1/certificatesearch", json={})
        resp.raise_for_status()
        return resp.json().get("certificates", [])

    # --- renew ------------------------------------------------------------
    def request_renewal(self, *, serial: str, idempotency_key: str) -> dict:
        """POST /certificaterequests — deterministic renewal (no LLM, no keys).

        Idempotent: replaying the same idempotency_key returns the same result.
        """
        if self.s.mode == "MOCK":
            return mock_inventory.request_renewal(serial=serial, idempotency_key=idempotency_key)
        resp = self.http.post(
            "/outagedetection/v1/certificaterequests",
            json={"existingCertificateId": serial, "idempotencyKey": idempotency_key},
        )
        resp.raise_for_status()
        return resp.json()

    def issuance_status(self, request_id: str) -> dict:
        if self.s.mode == "MOCK":
            return mock_inventory.issuance_status(request_id)
        resp = self.http.get(f"/outagedetection/v1/certificaterequests/{request_id}")
        resp.raise_for_status()
        return resp.json()


def _iso_in_days(days: int) -> str:
    from datetime import timedelta, timezone

    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


@lru_cache
def get_venafi_client() -> VenafiClient:
    return VenafiClient(get_settings())
