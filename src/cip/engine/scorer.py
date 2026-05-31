"""Risk scorer — PURE FUNCTION. Unit-tested to 100%.

    score = criticality_weight x (1 / max(days_left, 1))
    tier  = P1 if days_left < 7
            P2 if 8 <= days_left <= 30
            P3 if 31 <= days_left <= 90
            OK otherwise
    criticality_weight: prod x3, staging x2, dev/test x1

NO LLM. NO I/O. Deterministic date math + rule engine only.
"""
from __future__ import annotations

from dataclasses import dataclass

from cip.models import Tier

# Environment -> criticality weight (slide 5 / §5.2).
_ENV_WEIGHT = {"prod": 3, "staging": 2, "dev": 1, "test": 1}


def criticality_weight(environment: str) -> int:
    """prod x3, staging x2, dev/test x1. Unknown env defaults to 1."""
    return _ENV_WEIGHT.get(environment, 1)


def risk_score(environment: str, days_left: int) -> float:
    """score = weight x (1 / max(days_left, 1)). Higher = more urgent."""
    weight = criticality_weight(environment)
    return round(weight * (1.0 / max(days_left, 1)), 4)


def tier_for(days_left: int) -> Tier:
    """Deterministic tier banding.

    P1: days_left < 7 (includes already-expired, days_left < 0)
    P2: 7 <= days_left <= 30
    P3: 31 <= days_left <= 90
    OK: days_left > 90
    """
    if days_left < 7:
        return Tier.P1
    if days_left <= 30:
        return Tier.P2
    if days_left <= 90:
        return Tier.P3
    return Tier.OK


@dataclass(frozen=True)
class Score:
    risk_score: float
    tier: Tier
    weight: int
    days_left: int


def score(environment: str, days_left: int) -> Score:
    """Compute the full deterministic score for a certificate."""
    return Score(
        risk_score=risk_score(environment, days_left),
        tier=tier_for(days_left),
        weight=criticality_weight(environment),
        days_left=days_left,
    )
