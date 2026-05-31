"""Data model invariants — key_handling_policy never 'agent'; routing rule."""
from datetime import datetime, timedelta, timezone

import pytest

from cip.models import Certificate, Routing, route


def _cert(**kw):
    base = dict(
        serial="S1", thumbprint="t", common_name="api.example.com", ca="DigiCert",
        valid_from=datetime.now(timezone.utc) - timedelta(days=300),
        valid_to=datetime.now(timezone.utc) + timedelta(days=5),
        environment="prod", criticality="critical",
    )
    base.update(kw)
    return Certificate(**base)


def test_key_policy_agent_rejected():
    with pytest.raises(ValueError):
        _cert(key_handling_policy="agent")


def test_key_policy_valid():
    assert _cert(key_handling_policy="hsm").key_handling_policy == "hsm"


def test_routing_rule_bands():
    assert route(0.95) == Routing.AUTO
    assert route(0.80) == Routing.AUTO
    assert route(0.79) == Routing.AI_SUGGEST
    assert route(0.50) == Routing.AI_SUGGEST
    assert route(0.49) == Routing.STEWARD_TRIAGE
    assert route(0.0) == Routing.STEWARD_TRIAGE


def test_days_left():
    c = _cert()
    assert 4 <= c.days_left() <= 5
