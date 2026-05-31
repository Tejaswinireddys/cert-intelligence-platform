"""Notify agent — per-tier Teams messages. One message per cert per day max."""
from __future__ import annotations

from cip.agents import llm
from cip.agents.tools import registry
from cip.integrations.teams import get_teams
from cip.models import Certificate


@registry.register("send_teams_p1")
def _p1(*, title: str, text: str, action_label: str, cert_ref: str) -> dict:
    return get_teams().send(tier="P1", title=title, text=text,
                            action_label=action_label, cert_ref=cert_ref)


@registry.register("send_teams_p2")
def _p2(*, title: str, text: str, action_label: str, cert_ref: str) -> dict:
    return get_teams().send(tier="P2", title=title, text=text,
                            action_label=action_label, cert_ref=cert_ref)


@registry.register("send_teams_p3")
def _p3(*, title: str, text: str, action_label: str, cert_ref: str) -> dict:
    return get_teams().send(tier="P3", title=title, text=text,
                            action_label=action_label, cert_ref=cert_ref)


@registry.register("draft_message")
def _draft(*, tier: str, common_name: str, days_left: int, owner_group: str | None) -> dict:
    title, text, action = llm.draft_teams_message(
        tier=tier, common_name=common_name, days_left=days_left, owner_group=owner_group)
    return {"title": title, "text": text, "action_label": action}


def notify(cert: Certificate) -> dict:
    """Draft + send the per-tier card. Cert reference only — never a key."""
    draft = registry.call(agent="notify_agent", tool="draft_message",
                         args={"tier": cert.tier.value, "common_name": cert.common_name,
                               "days_left": cert.days_left(), "owner_group": cert.owner_group})
    tool = {"P1": "send_teams_p1", "P2": "send_teams_p2", "P3": "send_teams_p3"}[cert.tier.value]
    cert_ref = f"{cert.common_name} · serial {cert.serial[:12]}…"
    return registry.call(agent="notify_agent", tool=tool,
                        args={"title": draft["title"], "text": draft["text"],
                              "action_label": draft["action_label"], "cert_ref": cert_ref})
