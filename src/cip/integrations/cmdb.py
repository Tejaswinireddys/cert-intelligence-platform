"""CMDB adapter — ServiceNow / Jira Assets.

Returns ownership truth: CN/SAN -> service -> server CI -> app CI -> team.
MOCK mode derives a believable CMDB from the simulated Venafi fleet, with a
realistic fraction of incomplete records to exercise the orphan/AI-suggest path.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import httpx

from cip.audit import get_logger
from cip.config import Settings, get_settings
from cip.integrations.vault import read_secret
from cip.venafi import mock as venafi_mock

log = get_logger("cmdb")


class CmdbAdapter:
    def __init__(self, settings: Settings):
        self.s = settings
        self._index: Optional[dict[str, dict]] = None

    # --- mock index built from the simulated fleet ------------------------
    def _build_mock_index(self) -> dict[str, dict]:
        idx: dict[str, dict] = {}
        for c in venafi_mock.fleet():
            if c.get("owner_group") is None and c.get("application_ci") is None:
                continue  # genuine orphan — no CMDB record at all
            record = {
                "service": (c["common_name"].split(".")[0] if c.get("application_ci") else None),
                "server_ci": c.get("server_ci"),
                "application_ci": c.get("application_ci"),
                "owner_group": c.get("owner_group"),
                "escalation_path": c.get("escalation_path"),
            }
            for name in [c["common_name"], *c.get("sans", [])]:
                idx[name] = record
        return idx

    def lookup(self, *, common_name: str, sans: list[str]) -> Optional[dict]:
        if self.s.mode == "MOCK" or self.s.cmdb_kind == "mock":
            if self._index is None:
                self._index = self._build_mock_index()
            for name in [common_name, *sans]:
                if name in self._index:
                    return self._index[name]
            return None
        return self._lookup_live(common_name, sans)

    def _lookup_live(self, common_name: str, sans: list[str]) -> Optional[dict]:  # pragma: no cover
        token = read_secret(self.s.cmdb_token_path, actor="cmdb_agent", required=True)
        headers = {"Authorization": f"Bearer {token}"}
        # Example ServiceNow CMDB CI lookup by FQDN.
        with httpx.Client(base_url=self.s.cmdb_base_url, headers=headers, timeout=20.0) as h:
            r = h.get("/api/now/table/cmdb_ci_server", params={"sysparm_query": f"fqdn={common_name}"})
            r.raise_for_status()
            results = r.json().get("result", [])
            if not results:
                return None
            ci = results[0]
            return {
                "service": ci.get("service"),
                "server_ci": ci.get("sys_id"),
                "application_ci": ci.get("u_application"),
                "owner_group": ci.get("support_group"),
                "escalation_path": ci.get("escalation"),
            }

    def update_ci(self, *, server_ci: str, fields: dict) -> dict:
        """Write CI updates (cert->server link, owner, CA, policy)."""
        if self.s.mode == "MOCK":
            log.info("cmdb_update_mock", server_ci=server_ci, fields=fields)
            return {"server_ci": server_ci, "updated": True, **fields}
        token = read_secret(self.s.cmdb_token_path, actor="cmdb_agent", required=True)  # pragma: no cover
        with httpx.Client(base_url=self.s.cmdb_base_url, timeout=20.0,
                          headers={"Authorization": f"Bearer {token}"}) as h:  # pragma: no cover
            r = h.patch(f"/api/now/table/cmdb_ci_server/{server_ci}", json=fields)
            r.raise_for_status()
            return r.json()


@lru_cache
def get_cmdb() -> CmdbAdapter:
    return CmdbAdapter(get_settings())
