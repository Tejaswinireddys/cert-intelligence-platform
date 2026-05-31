"""Jira agent — create/update tickets carrying a cert REFERENCE (never a key)."""
from __future__ import annotations

from cip.agents import llm
from cip.agents.tools import registry
from cip.integrations.jira import get_jira
from cip.models import Certificate


@registry.register("create_ticket")
def _create_ticket(*, serial: str, summary: str, description: str, tier: str,
                   owner_group: str | None) -> dict:
    return get_jira().create_ticket(
        serial=serial, summary=summary, description=description, tier=tier,
        owner_group=owner_group,
    )


@registry.register("update_ticket")
def _update_ticket(*, key: str, tier: str, note: str) -> dict:
    return get_jira().update_ticket(key=key, tier=tier, note=note)


def create_or_update(cert: Certificate, *, existing_key: str | None = None) -> dict:
    """Build an enriched ticket (AI drafts the body) and create/update via the
    signed Jira tool. The agent only handles a cert reference — never a key."""
    description = llm.draft_jira_description(
        common_name=cert.common_name, sans=cert.sans, tier=cert.tier.value,
        environment=cert.environment, owner_group=cert.owner_group,
        days_left=cert.days_left(), ca=cert.ca,
    )
    summary = f"[{cert.tier.value}] Renew {cert.common_name} ({cert.environment}) — {cert.days_left()}d left"
    if existing_key:
        return registry.call(agent="jira_agent", tool="update_ticket",
                             args={"key": existing_key, "tier": cert.tier.value,
                                   "note": f"Tier now {cert.tier.value}; {cert.days_left()}d left"})
    return registry.call(agent="jira_agent", tool="create_ticket",
                        args={"serial": cert.serial, "summary": summary,
                              "description": description, "tier": cert.tier.value,
                              "owner_group": cert.owner_group})
