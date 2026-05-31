"""Dedup decision logic — MUST be 100% covered."""
from cip.engine.dedup import DedupAction, decide


def test_create_when_no_prior():
    d = decide(existing_tier=None, new_tier="P2")
    assert d.action == DedupAction.CREATE


def test_skip_when_unchanged():
    d = decide(existing_tier="P2", new_tier="P2", existing_jira_key="CERT-1")
    assert d.action == DedupAction.SKIP
    assert d.existing_jira_key == "CERT-1"


def test_update_on_escalation():
    d = decide(existing_tier="P3", new_tier="P1", existing_jira_key="CERT-9")
    assert d.action == DedupAction.UPDATE
    assert "P3 -> P1" in d.reason
    assert d.existing_jira_key == "CERT-9"


def test_update_on_deescalation():
    d = decide(existing_tier="P1", new_tier="P2")
    assert d.action == DedupAction.UPDATE
