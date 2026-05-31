"""Orchestrator agent — routes events to specialists, holds state.

Does NOT act on servers, hold keys, or approve production. It dispatches to the
Jira, Notify, Renewal, and CMDB specialist agents based on tier + routing.
"""
from __future__ import annotations

from cip.agents import cmdb_agent, jira_agent, notify_agent, renewal_agent  # noqa: F401 (registers tools)
from cip.agents.tools import registry
from cip.audit import get_logger
from cip.models import Certificate, Routing

log = get_logger("agent.orchestrator")


@registry.register("route_event")
def _route_event(*, serial: str, tier: str, routing: str) -> dict:
    return {"serial": serial, "tier": tier, "routing": routing, "dispatched": True}


def handle_cert(cert: Certificate, *, existing_jira_key: str | None = None) -> dict:
    """Dispatch a scored cert to specialists. Returns a summary of actions taken.

    - AUTO / AI_SUGGEST: create or update a Jira ticket + notify per tier.
    - STEWARD_TRIAGE: route to the orphan queue (no auto ticket to a team).
    """
    registry.call(agent="orchestrator", tool="route_event",
                 args={"serial": cert.serial, "tier": cert.tier.value, "routing": cert.routing.value})

    actions: dict = {"serial": cert.serial, "tier": cert.tier.value, "routing": cert.routing.value}

    if cert.routing == Routing.STEWARD_TRIAGE:
        actions["orphan"] = True
        return actions  # surfaced in dashboard orphan queue; no team ticket

    ticket = jira_agent.create_or_update(cert, existing_key=existing_jira_key)
    actions["jira"] = ticket.get("key")

    if cert.tier.value in ("P1", "P2", "P3"):
        notified = notify_agent.notify(cert)
        actions["notified"] = notified.get("tier")

    return actions
