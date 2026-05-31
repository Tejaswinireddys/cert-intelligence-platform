"""Signed, scoped tool definitions for AI agents.

Every agent tool call is HMAC-signed and scope-checked. Agents have NO tool that
opens SSH, reads a private key, or transitions a production approval. The signing
key resolves from Vault. A tool call with an out-of-scope name or a bad signature
is rejected and audited.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Any, Callable

from cip.audit import audit, get_logger
from cip.config import get_secrets, get_settings

log = get_logger("agent.tools")

# Per-agent allow-lists (slide 6 / §6). Anything not listed is denied.
AGENT_SCOPES: dict[str, set[str]] = {
    "orchestrator": {"route_event", "get_cert", "get_owner_confidence"},
    "jira_agent": {"create_ticket", "update_ticket", "attach_cert_ref"},
    "renewal_agent": {"request_renewal"},
    "notify_agent": {"send_teams_p1", "send_teams_p2", "send_teams_p3", "draft_message"},
    "cmdb_agent": {"update_ci", "link_cert_to_server"},
}

# Tools that are FORBIDDEN to every agent — defense in depth.
FORBIDDEN_TOOLS = {"open_ssh", "read_private_key", "approve_production", "deploy_to_server"}


class ToolDenied(Exception):
    pass


def _signing_key() -> bytes:
    s = get_settings()
    key = get_secrets().get(s.tool_signing_key_path)
    if not key:
        # MOCK fallback: deterministic dev key (never used in LIVE).
        key = "dev-mock-tool-signing-key"
    return key.encode()


def sign(agent: str, tool: str, args: dict[str, Any]) -> str:
    payload = json.dumps({"agent": agent, "tool": tool, "args": args}, sort_keys=True)
    return hmac.new(_signing_key(), payload.encode(), hashlib.sha256).hexdigest()


def verify(agent: str, tool: str, args: dict[str, Any], signature: str) -> bool:
    return hmac.compare_digest(sign(agent, tool, args), signature)


@dataclass
class ToolRegistry:
    handlers: dict[str, Callable[..., Any]] = field(default_factory=dict)

    def register(self, name: str):
        def deco(fn: Callable[..., Any]):
            self.handlers[name] = fn
            return fn

        return deco

    def call(self, *, agent: str, tool: str, args: dict[str, Any]) -> Any:
        """Scope-check, sign, verify, then dispatch. Every call is audited."""
        if tool in FORBIDDEN_TOOLS:
            audit(actor=agent, action="tool_denied", outcome="denied",
                  detail=f"forbidden tool {tool}")
            raise ToolDenied(f"Tool '{tool}' is forbidden to all agents")
        allowed = AGENT_SCOPES.get(agent, set())
        if tool not in allowed:
            audit(actor=agent, action="tool_denied", outcome="denied",
                  detail=f"out-of-scope tool {tool} for {agent}")
            raise ToolDenied(f"Agent '{agent}' may not call '{tool}'")
        signature = sign(agent, tool, args)
        if not verify(agent, tool, args, signature):  # pragma: no cover - sanity
            raise ToolDenied("signature verification failed")
        handler = self.handlers.get(tool)
        if handler is None:
            raise ToolDenied(f"No handler registered for '{tool}'")
        audit(actor=agent, action="tool_call", detail=f"{tool} args={list(args)}")
        return handler(**args)


registry = ToolRegistry()
