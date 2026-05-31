"""DedupGuard (DB-backed) — exercises the persistence path to 100%."""
from datetime import datetime, timezone

from cip.db import CertificateRow, EventRow, session_scope
from cip.engine.dedup import DedupAction, DedupGuard


def _seed_ticket(serial: str, idem: str, tier: str, jira_key: str):
    with session_scope() as s:
        s.add(CertificateRow(
            serial=serial, thumbprint="t", common_name=f"{serial}.example.com", sans=[],
            ca="DigiCert", valid_from=datetime(2025, 1, 1), valid_to=datetime(2026, 6, 3),
            environment="prod", criticality="critical", jira_key=jira_key, tier=tier,
        ))
        s.add(EventRow(id=serial + "ev", type="ticket_created", serial=serial, tier=tier,
                       idempotency_key=idem, actor="jira_agent", ts=datetime.now(timezone.utc)))


def test_guard_create_when_unseen():
    guard = DedupGuard()
    d = guard.check(idem_key="UNSEEN:2026-W01", new_tier="P2")
    assert d.action == DedupAction.CREATE


def test_guard_skip_when_same_tier():
    _seed_ticket("GD1", "GD1:2026-W23", "P2", "CERT-101")
    guard = DedupGuard()
    d = guard.check(idem_key="GD1:2026-W23", new_tier="P2")
    assert d.action == DedupAction.SKIP
    assert d.existing_jira_key == "CERT-101"


def test_guard_update_on_tier_change():
    _seed_ticket("GD2", "GD2:2026-W23", "P3", "CERT-102")
    guard = DedupGuard()
    d = guard.check(idem_key="GD2:2026-W23", new_tier="P1")
    assert d.action == DedupAction.UPDATE
    assert d.existing_jira_key == "CERT-102"
