"""WebSocket endpoint — live event push to connected dashboard clients.

Clients connect to WS /api/ws. The event bus calls enqueue_event() (thread-safe)
on every emit, which puts the payload into an asyncio.Queue. A background task
drains the queue and broadcasts to all connected clients.

The dashboard may fall back to polling /api/summary every 10 s if WS is unavailable.
"""
from __future__ import annotations

import asyncio
import json
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from cip.audit import get_logger
from cip.engine.bus import register_event_hook

log = get_logger("api.ws")

router = APIRouter()

_clients: Set[WebSocket] = set()
_queue: asyncio.Queue[dict] = asyncio.Queue()


def enqueue_event(payload: dict) -> None:
    """Thread-safe callback registered with the event bus.

    Called from the sync event bus (possibly a background scheduler thread).
    Uses call_soon_threadsafe so the asyncio queue is touched only from the
    event loop thread.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.call_soon_threadsafe(_queue.put_nowait, payload)
    except RuntimeError:
        pass


async def broadcast(payload: dict) -> None:
    """Send payload to all connected WebSocket clients; prune dead connections."""
    if not _clients:
        return
    msg = json.dumps(payload)
    dead: list[WebSocket] = []
    for ws in list(_clients):
        try:
            await ws.send_text(msg)
        except Exception:  # noqa: BLE001
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


async def broadcaster() -> None:
    """Long-running background task: drain the queue and broadcast to clients."""
    while True:
        payload = await _queue.get()
        await broadcast(payload)


@router.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    log.info("ws_connected", clients=len(_clients))
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        _clients.discard(ws)
        log.info("ws_disconnected", clients=len(_clients))


# Register as a hook immediately on import so any EventBus.emit() reaches us.
register_event_hook(enqueue_event)
