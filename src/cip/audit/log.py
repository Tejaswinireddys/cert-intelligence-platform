"""Append-only audit log + structured logging.

Write an append-only audit event for every renewal, deploy, and close.
The audit log NEVER contains key material — only cert references (serial).
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

import structlog

from cip.db import AuditRow, session_scope

# Patterns that must never be logged (defense-in-depth against key leakage).
_FORBIDDEN = ("BEGIN PRIVATE KEY", "BEGIN RSA PRIVATE KEY", "BEGIN EC PRIVATE KEY")


def _scrub(value: str) -> str:
    up = value.upper()
    if any(f in up for f in _FORBIDDEN):
        return "[REDACTED: key material blocked from logs]"
    return value


def _configure() -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


_configure()


def get_logger(name: str = "cip"):
    return structlog.get_logger(name)


def audit(
    *,
    actor: str,
    action: str,
    serial: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    outcome: str = "ok",
    detail: str = "",
) -> str:
    """Write one append-only audit row and emit a structured log line."""
    detail = _scrub(detail)
    rid = uuid.uuid4().hex
    with session_scope() as s:
        s.add(
            AuditRow(
                id=rid,
                actor=actor,
                action=action,
                serial=serial,
                idempotency_key=idempotency_key,
                outcome=outcome,
                detail=detail,
            )
        )
    get_logger("audit").info(
        "audit", actor=actor, action=action, serial=serial, outcome=outcome, detail=detail
    )
    return rid
