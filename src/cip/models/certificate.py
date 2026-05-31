"""Normalized certificate record + routing rule.

Build this first — the owner resolver and routing fail without clean inventory.
`key_handling_policy` may be 'workload' | 'venafi' | 'hsm' — NEVER 'agent'.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Environment = Literal["prod", "staging", "dev", "test"]
Criticality = Literal["critical", "high", "medium", "low"]


class Tier(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    OK = "OK"


class Routing(str, Enum):
    AUTO = "AUTO"  # >= 0.80 : create + route ticket to owner
    AI_SUGGEST = "AI_SUGGEST"  # 0.50-0.79 : AI suggests owner, human confirms
    STEWARD_TRIAGE = "STEWARD_TRIAGE"  # < 0.50 : certificate steward queue


def route(confidence: float) -> Routing:
    """Deterministic ownership routing rule (slide 7 / §4.2)."""
    if confidence >= 0.80:
        return Routing.AUTO
    if confidence >= 0.50:
        return Routing.AI_SUGGEST
    return Routing.STEWARD_TRIAGE


class Certificate(BaseModel):
    serial: str  # primary identity
    thumbprint: str
    common_name: str
    sans: list[str] = Field(default_factory=list)
    ca: str
    template: Optional[str] = None
    valid_from: datetime
    valid_to: datetime
    environment: Environment
    criticality: Criticality
    application_ci: Optional[str] = None  # from CMDB
    server_ci: Optional[str] = None  # from CMDB
    owner_group: Optional[str] = None
    escalation_path: Optional[str] = None
    renewal_method: Optional[str] = None  # acme | venafi-driver | ansible | manual
    deploy_method: Optional[str] = None
    key_handling_policy: str = "venafi"  # workload | venafi | hsm  (NEVER "agent")
    last_verified_endpoint: Optional[str] = None
    last_verified_port: Optional[int] = None

    # Derived / runtime fields (populated by engine + agents)
    risk_score: float = 0.0
    tier: Tier = Tier.OK
    owner_confidence: float = 0.0
    routing: Routing = Routing.STEWARD_TRIAGE
    status: str = "open"  # open | approved | renewed | deployed | verified | closed | renewed-not-deployed
    jira_key: Optional[str] = None

    @field_validator("key_handling_policy")
    @classmethod
    def _no_agent_keys(cls, v: str) -> str:
        if v == "agent":
            raise ValueError("key_handling_policy must never be 'agent' (private-key constraint)")
        return v

    def days_left(self, *, now: Optional[datetime] = None) -> int:
        now = now or datetime.now(timezone.utc)
        vt = self.valid_to
        if vt.tzinfo is None:
            vt = vt.replace(tzinfo=timezone.utc)
        return (vt - now).days
