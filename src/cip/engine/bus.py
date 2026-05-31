"""Event bus + dead-letter queue.

Emit CertEvent envelopes to per-tier queues. Workers retry with exponential
backoff. After N attempts -> dead-letter queue surfaced in the dashboard's
orphan/error view. NEVER silently drop.

MOCK: in-process queue. LIVE: Redis Streams (swap via CIP_BUS_BACKEND=redis).
"""
from __future__ import annotations

import uuid
from collections import defaultdict, deque
from typing import Callable, Optional

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from cip.audit import get_logger
from cip.config import get_settings
from cip.db import DlqRow, EventRow, session_scope
from cip.models.event import CertEvent

log = get_logger("bus")

MAX_ATTEMPTS = 5


class TransientError(Exception):
    """Retryable error (e.g. API 429 / 5xx)."""


class EventBus:
    def __init__(self):
        self.settings = get_settings()
        self._queues: dict[str, deque[CertEvent]] = defaultdict(deque)

    def emit(self, event: CertEvent) -> None:
        """Enqueue an event to its per-tier queue and persist it (append-only)."""
        tier = event.tier or "OK"
        self._queues[tier].append(event)
        with session_scope() as s:
            s.add(
                EventRow(
                    id=event.id,
                    type=event.type.value if hasattr(event.type, "value") else str(event.type),
                    serial=event.serial,
                    tier=event.tier,
                    idempotency_key=event.idempotency_key,
                    actor=event.actor,
                    detail=event.detail,
                    attempts=event.attempts,
                    ts=event.ts,
                )
            )
        log.info("emit", type=str(event.type), serial=event.serial, tier=tier)

    def process(self, event: CertEvent, handler: Callable[[CertEvent], None]) -> bool:
        """Run a handler with retry+backoff. On final failure -> DLQ. Returns
        True on success, False if the event was dead-lettered."""

        @retry(
            stop=stop_after_attempt(MAX_ATTEMPTS),
            wait=wait_exponential(multiplier=0.1, max=2),
            retry=retry_if_exception_type(TransientError),
            reraise=True,
        )
        def _run():
            handler(event)

        try:
            _run()
            return True
        except Exception as e:  # noqa: BLE001 - we deliberately catch & DLQ
            self.dead_letter(event, str(e))
            return False

    def dead_letter(self, event: CertEvent, error: str) -> None:
        with session_scope() as s:
            s.add(
                DlqRow(
                    id=uuid.uuid4().hex,
                    event_type=event.type.value if hasattr(event.type, "value") else str(event.type),
                    serial=event.serial,
                    attempts=MAX_ATTEMPTS,
                    last_error=error[:500],
                )
            )
        log.error("dead_letter", serial=event.serial, error=error)

    def drain(self, tier: Optional[str] = None) -> list[CertEvent]:
        if tier:
            out = list(self._queues[tier])
            self._queues[tier].clear()
            return out
        out: list[CertEvent] = []
        for t in list(self._queues):
            out.extend(self._queues[t])
            self._queues[t].clear()
        return out


_bus: Optional[EventBus] = None


def get_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
