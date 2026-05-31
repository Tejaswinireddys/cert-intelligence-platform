"""Microsoft Teams adapter — per-tier notifications.

One message per cert per day maximum. Owners must see exactly one action per
message. P1 immediate page; P2 daily card; P3 weekly digest. Never key material.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import httpx

from cip.audit import get_logger
from cip.config import Settings, get_settings
from cip.integrations.vault import read_secret

log = get_logger("teams")


class TeamsAdapter:
    def __init__(self, settings: Settings):
        self.s = settings
        self._sent: list[dict] = []  # mock outbox

    def _webhook(self, tier: str) -> str:
        path = {
            "P1": self.s.teams_p1_webhook_path,
            "P2": self.s.teams_p2_webhook_path,
            "P3": self.s.teams_p3_webhook_path,
        }.get(tier, self.s.teams_p3_webhook_path)
        return read_secret(path, actor="notify_agent")

    def send(self, *, tier: str, title: str, text: str, action_label: str,
             cert_ref: str) -> dict:
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": {"P1": "EF4444", "P2": "F59E0B", "P3": "22C55E"}.get(tier, "64748B"),
            "summary": title,
            "title": title,
            "text": text,
            "sections": [{"facts": [{"name": "Cert reference", "value": cert_ref}]}],
            "potentialAction": [{"@type": "OpenUri", "name": action_label,
                                  "targets": [{"os": "default", "uri": "https://cert-dashboard.internal"}]}],
        }
        if self.s.mode == "MOCK":
            entry = {"tier": tier, "title": title, "cert_ref": cert_ref, "card": card}
            self._sent.append(entry)
            log.info("teams_send_mock", tier=tier, cert_ref=cert_ref, title=title)
            return {"sent": True, "tier": tier}
        webhook = self._webhook(tier)  # pragma: no cover
        with httpx.Client(timeout=15.0) as h:  # pragma: no cover
            r = h.post(webhook, json=card)
            r.raise_for_status()
            return {"sent": True, "status": r.status_code}

    @property
    def outbox(self) -> list[dict]:
        return self._sent


@lru_cache
def get_teams() -> TeamsAdapter:
    return TeamsAdapter(get_settings())
