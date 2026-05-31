"""Agent tools must be signed + scoped; forbidden tools always denied."""
import pytest

from cip.agents.tools import ToolDenied, registry


def test_forbidden_tool_denied_for_all():
    for tool in ("open_ssh", "read_private_key", "approve_production", "deploy_to_server"):
        with pytest.raises(ToolDenied):
            registry.call(agent="orchestrator", tool=tool, args={})


def test_out_of_scope_tool_denied():
    # renewal_agent may not create Jira tickets.
    with pytest.raises(ToolDenied):
        registry.call(agent="renewal_agent", tool="create_ticket", args={})


def test_no_agent_can_handle_keys():
    # No agent scope includes any key/ssh tool.
    from cip.agents.tools import AGENT_SCOPES, FORBIDDEN_TOOLS

    for scope in AGENT_SCOPES.values():
        assert not (scope & FORBIDDEN_TOOLS)
