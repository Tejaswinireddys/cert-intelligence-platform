"""Idempotency tests — a replayed renewal can never duplicate."""
from datetime import datetime, timezone

from cip.models.event import idempotency_key, renewal_window
from cip.venafi import mock


def test_idempotency_key_format():
    vt = datetime(2026, 6, 3, tzinfo=timezone.utc)
    key = idempotency_key("ABC123", vt)
    assert key.startswith("ABC123:")
    assert "-W" in key


def test_renewal_window_is_iso_week():
    vt = datetime(2026, 6, 3, tzinfo=timezone.utc)
    win = renewal_window(vt)
    assert win == f"{vt.isocalendar().year}-W{vt.isocalendar().week:02d}"


def test_renewal_request_is_idempotent():
    mock.reset_renewals()
    r1 = mock.request_renewal(serial="S1", idempotency_key="S1:2026-W23")
    r2 = mock.request_renewal(serial="S1", idempotency_key="S1:2026-W23")
    # Same idempotency key -> identical request id (no second issuance).
    assert r1["requestId"] == r2["requestId"]
    assert r1["newSerial"] == r2["newSerial"]


def test_different_window_is_distinct():
    mock.reset_renewals()
    r1 = mock.request_renewal(serial="S1", idempotency_key="S1:2026-W23")
    r2 = mock.request_renewal(serial="S1", idempotency_key="S1:2026-W24")
    assert r1["requestId"] != r2["requestId"]
