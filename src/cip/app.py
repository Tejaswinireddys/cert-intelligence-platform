"""FastAPI application factory — dashboard backend + webhook receivers."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cip import __version__
from cip.api import dashboard, webhooks, ws  # ws import registers the event hook
from cip.audit import get_logger
from cip.config import get_settings
from cip.db import CertificateRow, create_all, session_scope

log = get_logger("app")


def _seed_if_empty() -> None:
    """Run an initial scan so the dashboard is populated on first boot (MOCK)."""
    with session_scope() as s:
        count = s.query(CertificateRow).count()
    if count == 0:
        from cip.engine import scanner

        log.info("seeding_initial_scan")
        scanner.scan()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all()
    _seed_if_empty()
    if get_settings().mode == "MOCK":
        # In MOCK we still start the scheduler so the daily job is registered.
        try:
            from cip.scheduler import start_scheduler

            start_scheduler()
        except Exception as e:  # noqa: BLE001
            log.warning("scheduler_skipped", error=str(e))
    # Background task: drain the event-bus → WebSocket broadcast queue.
    broadcaster_task = asyncio.create_task(ws.broadcaster())
    yield
    broadcaster_task.cancel()
    try:
        await broadcaster_task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Certificate Intelligence Platform", version=__version__,
                  lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=s.cors_origin_list, allow_methods=["*"],
        allow_headers=["*"], allow_credentials=True,
    )

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "mode": s.mode, "version": __version__,
                "time": datetime.now(timezone.utc).isoformat()}

    app.include_router(dashboard.router)
    app.include_router(webhooks.router)
    app.include_router(ws.router)
    return app


app = create_app()
