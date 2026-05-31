"""LLM helper — enrichment + drafting only.

In MOCK mode (or when no OpenAI key is present) this returns high-quality
template-based drafts so the platform runs end-to-end with no API key. In LIVE
mode it calls OpenAI with tool-use. The LLM NEVER sees key material — callers
pass cert references (serial/thumbprint), CN, SANs, tier, owner only.
"""
from __future__ import annotations

from cip.audit import get_logger
from cip.config import get_secrets, get_settings

log = get_logger("agent.llm")


def _openai_available() -> bool:
    s = get_settings()
    if s.mode != "LIVE":
        return False
    return bool(get_secrets().get(s.openai_apikey_path))


def draft_jira_description(*, common_name: str, sans: list[str], tier: str,
                          environment: str, owner_group: str | None, days_left: int,
                          ca: str) -> str:
    """Draft a Jira ticket body with real impact context — no key material."""
    san_str = ", ".join(sans)
    impact = f"covers {san_str}" if len(sans) > 1 else f"covers {common_name}"
    base = (
        f"Certificate {common_name} ({environment}) expires in {days_left} day(s) "
        f"[risk tier {tier}].\n\n"
        f"Impact: this certificate {impact} — all {environment}. Issued by {ca}.\n"
        f"Owner: {owner_group or 'UNRESOLVED — steward triage'}.\n\n"
        f"Action required: renew before expiry. Cert reference only (no key material "
        f"is attached to this ticket per policy)."
    )
    if not _openai_available():
        return base
    return _openai_enrich(base, kind="jira")  # pragma: no cover


def draft_teams_message(*, tier: str, common_name: str, days_left: int,
                        owner_group: str | None) -> tuple[str, str, str]:
    """Return (title, text, action_label) for a per-tier Teams card."""
    if tier == "P1":
        title = f"🔴 P1 cert expiring: {common_name}"
        text = (f"{common_name} expires in {days_left} day(s). Immediate action required. "
                f"Owner: {owner_group or 'on-call'}. Re-ping every 2h; CISO after 4h.")
        action = "Renew now"
    elif tier == "P2":
        title = f"🟠 P2 cert renewal due: {common_name}"
        text = (f"{common_name} expires in {days_left} day(s). Please schedule renewal. "
                f"Owner: {owner_group or 'team'}. Auto-escalates to P1 after 3 days.")
        action = "View ticket"
    else:
        title = f"🟢 P3 weekly digest: {common_name}"
        text = (f"{common_name} expires in {days_left} day(s). Tracked, no action needed yet. "
                f"Owner: {owner_group or 'team leads'}.")
        action = "Review"
    return title, text, action


def suggest_owner(*, common_name: str, sans: list[str],
                  candidates: list[str]) -> tuple[str, float]:
    """Suggest an owner when CMDB is ambiguous (0.50-0.79 band).

    Deterministic-ish heuristic in MOCK: match service prefix to a candidate.
    Returns (suggested_owner, confidence). Logged against human-final later.
    """
    service = common_name.split(".")[0].lower()
    keyword_map = {
        "checkout": "Commerce", "billing": "Payments Platform", "pay": "Payments Platform",
        "auth": "Identity", "login": "Identity", "cdn": "Edge / CDN", "static": "Edge / CDN",
        "data": "Data Platform", "events": "Data Platform", "mobile": "Mobile Backend",
        "admin": "Internal Tools", "metrics": "Data Platform",
    }
    guess = keyword_map.get(service)
    if guess and (not candidates or guess in candidates):
        return guess, 0.66
    if candidates:
        return candidates[0], 0.55
    return "Internal Tools", 0.52


def _openai_enrich(text: str, *, kind: str) -> str:  # pragma: no cover - needs key
    from openai import OpenAI

    s = get_settings()
    client = OpenAI(api_key=get_secrets().get(s.openai_apikey_path, required=True))
    resp = client.chat.completions.create(
        model=s.openai_model,
        messages=[
            {"role": "system", "content": "You enrich certificate-renewal tickets with "
                                          "concrete impact. Never include key material."},
            {"role": "user", "content": text},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content or text
