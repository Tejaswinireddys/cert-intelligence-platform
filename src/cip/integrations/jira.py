"""Jira adapter — create/update tickets carrying a cert REFERENCE only.

NEVER attach private key material. Tickets carry serial/thumbprint, CN, SANs,
risk tier, owner, deploy log — never a key.
"""
from __future__ import annotations

import hashlib
import itertools
from functools import lru_cache
from typing import Optional

import httpx

from cip.audit import get_logger
from cip.config import Settings, get_settings
from cip.integrations.vault import read_secret

log = get_logger("jira")

_FORBIDDEN_KEY_MARKERS = ("PRIVATE KEY", "BEGIN RSA", "BEGIN EC")


def _assert_no_key(text: str) -> None:
    up = text.upper()
    if any(m in up for m in _FORBIDDEN_KEY_MARKERS):
        raise ValueError("Refusing to write key material into Jira (private-key constraint)")


class JiraAdapter:
    def __init__(self, settings: Settings):
        self.s = settings
        self._counter = itertools.count(300)
        self._mock_store: dict[str, dict] = {}

    def _key_for(self, serial: str) -> str:
        n = 300 + (int(hashlib.sha1(serial.encode()).hexdigest()[:4], 16) % 700)
        return f"{self.s.jira_default_project}-{n}"

    def create_ticket(self, *, serial: str, summary: str, description: str, tier: str,
                       owner_group: Optional[str]) -> dict:
        _assert_no_key(summary)
        _assert_no_key(description)
        if self.s.mode == "MOCK":
            key = self._key_for(serial)
            self._mock_store[key] = {
                "key": key, "serial": serial, "tier": tier, "status": "Open",
                "owner_group": owner_group, "summary": summary,
            }
            log.info("jira_create_mock", key=key, serial=serial, tier=tier)
            return self._mock_store[key]
        return self._create_live(serial, summary, description, tier, owner_group)

    def _create_live(self, serial, summary, description, tier, owner_group):  # pragma: no cover
        user = read_secret(self.s.jira_user_path, actor="jira_agent", required=True)
        token = read_secret(self.s.jira_token_path, actor="jira_agent", required=True)
        payload = {
            "fields": {
                "project": {"key": self.s.jira_default_project},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Task"},
                "labels": [f"cert-{tier.lower()}", "cert-intelligence"],
            }
        }
        with httpx.Client(base_url=self.s.jira_base_url, auth=(user, token), timeout=20.0) as h:
            r = h.post("/rest/api/3/issue", json=payload)
            r.raise_for_status()
            return r.json()

    def update_ticket(self, *, key: str, tier: str, note: str) -> dict:
        _assert_no_key(note)
        if self.s.mode == "MOCK":
            tk = self._mock_store.get(key, {"key": key})
            tk["tier"] = tier
            tk["last_note"] = note
            log.info("jira_update_mock", key=key, tier=tier)
            return tk
        return {"key": key, "updated": True}  # pragma: no cover

    def transition_approve(self, *, key: str) -> dict:
        """Simulate a Jira approval transition (the production human gate)."""
        if self.s.mode == "MOCK":
            tk = self._mock_store.get(key, {"key": key})
            tk["status"] = "Approved"
            log.info("jira_approve_mock", key=key)
            return tk
        return {"key": key, "status": "Approved"}  # pragma: no cover

    def get(self, key: str) -> Optional[dict]:
        return self._mock_store.get(key)


@lru_cache
def get_jira() -> JiraAdapter:
    return JiraAdapter(get_settings())
