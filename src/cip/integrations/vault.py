"""Vault / KMS adapter.

All API credentials load from Vault/KMS at runtime. `.env` holds paths only.
This wraps the SecretResolver in config.py and adds an append-only
secret-access audit log so security can prove each access.
"""
from __future__ import annotations

from cip.audit import audit, get_logger
from cip.config import get_secrets

log = get_logger("vault")


def read_secret(path: str, *, actor: str, required: bool = False) -> str:
    """Read a secret by path and write a secret-access audit event.

    Returns "" in MOCK mode when the secret is not set, allowing adapters to
    fall back to simulation.
    """
    value = get_secrets().get(path, required=required)
    audit(
        actor=actor,
        action="secret_access",
        detail=f"path={path} present={bool(value)}",
        outcome="ok" if value or not required else "missing",
    )
    return value
