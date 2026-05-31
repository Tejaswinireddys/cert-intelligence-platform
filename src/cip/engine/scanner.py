"""Scanner — daily (and on-demand) expiry scan. DETERMINISTIC, no LLM.

Calls Venafi certificatesearch by validityEnd for each window, normalizes into
Certificate rows, scores, resolves ownership + confidence, applies the dedup
guard, emits events, and hands AUTO/AI_SUGGEST certs to the orchestrator.
"""
from __future__ import annotations

from datetime import datetime, timezone

from cip.agents import orchestrator
from cip.audit import audit, get_logger
from cip.config import get_settings
from cip.db import CertificateRow, session_scope
from cip.engine import scorer
from cip.engine.bus import get_bus
from cip.engine.dedup import DedupAction, DedupGuard
from cip.engine.resolver import resolve, routing_for
from cip.models import Certificate, Routing, Tier
from cip.models.event import CertEvent, EventType, idempotency_key
from cip.venafi import get_venafi_client

log = get_logger("engine.scanner")


def _normalize(raw: dict) -> Certificate:
    return Certificate(
        serial=raw["serial"], thumbprint=raw["thumbprint"], common_name=raw["common_name"],
        sans=raw.get("sans", []), ca=raw["ca"], template=raw.get("template"),
        valid_from=datetime.fromisoformat(raw["valid_from"]),
        valid_to=datetime.fromisoformat(raw["valid_to"]),
        environment=raw["environment"], criticality=raw["criticality"],
        application_ci=raw.get("application_ci"), server_ci=raw.get("server_ci"),
        owner_group=raw.get("owner_group"), escalation_path=raw.get("escalation_path"),
        renewal_method=raw.get("renewal_method"), deploy_method=raw.get("deploy_method"),
        key_handling_policy=raw.get("key_handling_policy", "venafi"),
        last_verified_endpoint=raw.get("last_verified_endpoint"),
        last_verified_port=raw.get("last_verified_port"),
    )


def _persist(cert: Certificate) -> None:
    with session_scope() as s:
        row = s.get(CertificateRow, cert.serial)
        data = dict(
            thumbprint=cert.thumbprint, common_name=cert.common_name, sans=cert.sans,
            ca=cert.ca, template=cert.template, valid_from=cert.valid_from.replace(tzinfo=None),
            valid_to=cert.valid_to.replace(tzinfo=None), environment=cert.environment,
            criticality=cert.criticality, application_ci=cert.application_ci,
            server_ci=cert.server_ci, owner_group=cert.owner_group,
            escalation_path=cert.escalation_path, renewal_method=cert.renewal_method,
            deploy_method=cert.deploy_method, key_handling_policy=cert.key_handling_policy,
            last_verified_endpoint=cert.last_verified_endpoint,
            last_verified_port=cert.last_verified_port, risk_score=cert.risk_score,
            tier=cert.tier.value, owner_confidence=cert.owner_confidence,
            routing=cert.routing.value, status=cert.status, jira_key=cert.jira_key,
        )
        if row is None:
            s.add(CertificateRow(serial=cert.serial, **data))
        else:
            for k, v in data.items():
                setattr(row, k, v)


def scan(windows: list[int] | None = None, *, now: datetime | None = None,
         include_healthy: bool = True) -> dict:
    """Run a full scan across the configured windows. Returns counts.

    When include_healthy is True, the full inventory is ingested (healthy >90d
    certs are tracked but never ticketed) so the dashboard reflects the whole
    fleet. Ticketing/notification only fire for expiring (non-OK) certs.

    After the main loop, AUTO-routed dev/test certs that are new this renewal
    window (DedupAction.CREATE) are automatically kicked through the renewal saga
    — no human approval required for non-prod environments.
    """
    settings = get_settings()
    windows = windows or settings.scan_window_list
    now = now or datetime.now(timezone.utc)
    client = get_venafi_client()
    bus = get_bus()
    guard = DedupGuard()

    seen: set[str] = set()
    tier_counts = {"P1": 0, "P2": 0, "P3": 0, "OK": 0}
    new_events = 0
    # Collect serials eligible for auto-renewal (AUTO, dev/test, newly-created this window).
    auto_renew_queue: list[str] = []

    # Scan widest window once (covers all narrower ones) for the mock; LIVE may
    # iterate per-window for API efficiency.
    raw_certs = client.search_all() if include_healthy else client.search_expiring(max(windows))

    for raw in raw_certs:
        cert = _normalize(raw)
        if cert.serial in seen:
            continue
        seen.add(cert.serial)

        days = cert.days_left(now=now)
        sc = scorer.score(cert.environment, days)
        cert.risk_score = sc.risk_score
        cert.tier = sc.tier

        # Deterministic ownership resolution + confidence routing.
        resolution = resolve(cert)
        cert.owner_confidence = resolution.confidence
        cert.owner_group = resolution.owner_group or cert.owner_group
        cert.escalation_path = resolution.escalation_path or cert.escalation_path
        cert.routing = routing_for(resolution.confidence)

        idem = idempotency_key(cert.serial, cert.valid_to)

        # Dedup guard: create vs update vs skip.
        decision = guard.check(idem_key=idem, new_tier=cert.tier.value)

        # SCANNED + SCORED events (append-only).
        bus.emit(CertEvent(type=EventType.SCANNED, serial=cert.serial, tier=cert.tier.value,
                           idempotency_key=idem, detail=f"{days}d left"))
        bus.emit(CertEvent(type=EventType.SCORED, serial=cert.serial, tier=cert.tier.value,
                           idempotency_key=idem,
                           detail=f"score={cert.risk_score} conf={cert.owner_confidence}"))
        new_events += 2

        if cert.tier.value in tier_counts:
            tier_counts[cert.tier.value] += 1

        # Persist before dispatch so the dashboard reflects state immediately.
        _persist(cert)

        # Only act on non-OK certs. OK certs are tracked but not ticketed.
        if cert.tier == Tier.OK:
            continue

        if decision.action == DedupAction.SKIP:
            continue

        # Dispatch to orchestrator (creates/updates ticket + notifies).
        try:
            actions = orchestrator.handle_cert(
                cert, existing_jira_key=decision.existing_jira_key
            )
            if actions.get("jira"):
                cert.jira_key = actions["jira"]
                _persist(cert)
                ev_type = (EventType.TICKET_CREATED if decision.action == DedupAction.CREATE
                           else EventType.TICKET_UPDATED)
                bus.emit(CertEvent(type=ev_type, serial=cert.serial, tier=cert.tier.value,
                                   idempotency_key=idem, actor="jira_agent",
                                   detail=f"jira={cert.jira_key}"))
                new_events += 1
            if actions.get("notified"):
                bus.emit(CertEvent(type=EventType.NOTIFIED, serial=cert.serial,
                                   tier=cert.tier.value, idempotency_key=idem,
                                   actor="notify_agent", detail=f"tier {cert.tier.value} card"))
                new_events += 1
        except Exception as e:  # noqa: BLE001 - route failures to DLQ, never drop
            bus.dead_letter(
                CertEvent(type=EventType.TICKET_CREATED, serial=cert.serial,
                          tier=cert.tier.value, idempotency_key=idem), str(e)
            )
            continue

        # Queue AUTO dev/test certs for immediate saga execution (no approval needed).
        if (decision.action == DedupAction.CREATE and
                cert.routing == Routing.AUTO and
                cert.environment in ("dev", "test")):
            auto_renew_queue.append(cert.serial)

    # Auto-renewal pass: run saga for newly-discovered AUTO non-prod certs.
    # This runs after the scan loop so DB writes are committed before saga reads them.
    if auto_renew_queue:
        from cip.execution import saga  # local import to avoid module-level circularity

        log.info("auto_renew_start", count=len(auto_renew_queue))
        for serial in auto_renew_queue:
            try:
                result = saga.run_saga(serial, now=now)
                log.info("auto_renew_result", serial=serial, saga=result.get("saga"))
            except Exception as e:  # noqa: BLE001
                log.error("auto_renew_error", serial=serial, error=str(e))
                bus.dead_letter(
                    CertEvent(type=EventType.RENEWAL_REQUESTED, serial=serial,
                              tier="", idempotency_key=f"{serial}:auto"), str(e)
                )

    audit(actor="engine", action="scan_complete",
          detail=f"scanned={len(seen)} tiers={tier_counts} auto_renewed={len(auto_renew_queue)}")
    return {"scanned": len(seen), "new_events": new_events, "tier_counts": tier_counts}
