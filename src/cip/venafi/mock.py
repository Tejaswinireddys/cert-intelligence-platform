"""Simulated Venafi inventory — powers MOCK mode end-to-end.

Generates a realistic, deterministic certificate fleet (seeded RNG) spread
across expiry windows, environments, owner groups, CAs and deploy methods so
the dashboard shows a believable heatmap, tier mix, and orphan queue.

This module returns METADATA ONLY — never private keys.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone

_SEED = 1337
_NOW = datetime.now(timezone.utc)

_OWNER_GROUPS = [
    ("Payments Platform", "payments-oncall", "PAY"),
    ("Identity", "identity-oncall", "IDN"),
    ("Edge / CDN", "edge-oncall", "EDGE"),
    ("Data Platform", "data-oncall", "DATA"),
    ("Internal Tools", "tools-oncall", "TOOL"),
    ("Commerce", "commerce-oncall", "COM"),
    ("Mobile Backend", "mobile-oncall", "MOB"),
]
_CAS = ["DigiCert", "Let's Encrypt", "Internal-PKI", "Sectigo", "GlobalSign"]
_ENVS = ["prod", "prod", "prod", "staging", "dev", "test"]  # weighted toward prod
_CRIT = {"prod": "critical", "staging": "high", "dev": "medium", "test": "low"}
_DEPLOY = ["venafi-driver", "acme", "ansible", "manual"]
_KEY_POLICY = {"venafi-driver": "venafi", "acme": "workload", "ansible": "workload", "manual": "hsm"}
_DOMAINS = [
    "api", "auth", "checkout", "cdn", "internal", "data", "events", "login",
    "gateway", "billing", "search", "media", "static", "admin", "metrics",
]
_TLDS = ["example.com", "example.net", "corp.example.com", "svc.internal"]

# How many certs fall into each expiry window (days-left).
_WINDOW_PLAN = [
    (-5, 2),    # already expired (surface as P1 critical)
    (3, 4),     # < 7 -> P1
    (6, 3),     # < 7 -> P1
    (12, 7),    # 8-30 -> P2
    (22, 6),    # 8-30 -> P2
    (28, 5),    # 8-30 -> P2
    (45, 9),    # 31-90 -> P3
    (67, 8),    # 31-90 -> P3
    (88, 7),    # 31-90 -> P3
    (140, 30),  # > 90 -> OK
    (250, 28),  # > 90 -> OK
]


def _rng() -> random.Random:
    return random.Random(_SEED)


def _mk_serial(i: int) -> str:
    return hashlib.sha1(f"cert-{i}-{_SEED}".encode()).hexdigest()[:24].upper()


def _mk_thumb(serial: str) -> str:
    return "sha1:" + hashlib.sha1(serial.encode()).hexdigest()


def _build_fleet() -> list[dict]:
    r = _rng()
    fleet: list[dict] = []
    idx = 0
    for days_left, count in _WINDOW_PLAN:
        for _ in range(count):
            idx += 1
            serial = _mk_serial(idx)
            env = r.choice(_ENVS)
            og_name, esc, proj = r.choice(_OWNER_GROUPS)
            n_sans = r.randint(1, 3)
            base = r.choice(_DOMAINS)
            tld = r.choice(_TLDS)
            cn = f"{base}.{tld}"
            sans = [cn] + [f"{r.choice(_DOMAINS)}.{tld}" for _ in range(n_sans - 1)]
            sans = sorted(set(sans))
            deploy = r.choice(_DEPLOY)
            valid_to = _NOW + timedelta(days=days_left)
            valid_from = valid_to - timedelta(days=r.choice([90, 200, 397]))

            # ~12% of certs have missing/ambiguous CMDB data -> orphan/AI-suggest.
            cmdb_quality = r.random()
            if cmdb_quality < 0.06:
                app_ci = server_ci = owner_group = escalation = None  # orphan
            elif cmdb_quality < 0.14:
                app_ci = f"APP-{1000 + idx}"
                server_ci = None  # partial -> AI suggest band
                owner_group = og_name
                escalation = esc
            else:
                app_ci = f"APP-{1000 + idx}"
                server_ci = f"SRV-{3000 + idx}"
                owner_group = og_name
                escalation = esc

            fleet.append(
                {
                    "serial": serial,
                    "thumbprint": _mk_thumb(serial),
                    "common_name": cn,
                    "sans": sans,
                    "ca": r.choice(_CAS),
                    "template": f"{env}-tls",
                    "valid_from": valid_from.isoformat(),
                    "valid_to": valid_to.isoformat(),
                    "environment": env,
                    "criticality": _CRIT[env],
                    "application_ci": app_ci,
                    "server_ci": server_ci,
                    "owner_group": owner_group,
                    "escalation_path": escalation,
                    "renewal_method": deploy,
                    "deploy_method": deploy,
                    "key_handling_policy": _KEY_POLICY[deploy],
                    "last_verified_endpoint": cn,
                    "last_verified_port": 443,
                    "_project": proj,
                }
            )
    return fleet


_FLEET: list[dict] | None = None


def fleet() -> list[dict]:
    global _FLEET
    if _FLEET is None:
        _FLEET = _build_fleet()
    return _FLEET


def search_expiring(within_days: int) -> list[dict]:
    out = []
    for c in fleet():
        vt = datetime.fromisoformat(c["valid_to"])
        days = (vt - _NOW).days
        if days <= within_days:
            out.append(c)
    return out


def search_all() -> list[dict]:
    """Full inventory, including healthy (>90d) certs — tracked but not ticketed."""
    return list(fleet())


# --- renewal simulation ----------------------------------------------------
_RENEWALS: dict[str, dict] = {}


def request_renewal(*, serial: str, idempotency_key: str) -> dict:
    # Idempotent: same key -> same request id.
    if idempotency_key in _RENEWALS:
        return _RENEWALS[idempotency_key]
    req_id = "req-" + hashlib.sha1(idempotency_key.encode()).hexdigest()[:16]
    result = {
        "requestId": req_id,
        "serial": serial,
        "idempotencyKey": idempotency_key,
        "status": "ISSUED",
        "newSerial": _mk_serial(int(hashlib.sha1(serial.encode()).hexdigest()[:6], 16)),
    }
    _RENEWALS[idempotency_key] = result
    return result


def issuance_status(request_id: str) -> dict:
    return {"requestId": request_id, "status": "ISSUED"}


def reset_renewals() -> None:
    _RENEWALS.clear()
