"""Scorer unit tests — MUST be 100% covered (deterministic logic)."""
import pytest

from cip.engine import scorer
from cip.models import Tier


@pytest.mark.parametrize(
    "env,expected", [("prod", 3), ("staging", 2), ("dev", 1), ("test", 1), ("unknown", 1)]
)
def test_criticality_weight(env, expected):
    assert scorer.criticality_weight(env) == expected


def test_risk_score_formula():
    # prod x3, 10 days left -> 3 * (1/10) = 0.3
    assert scorer.risk_score("prod", 10) == 0.3
    # staging x2, 5 days -> 0.4
    assert scorer.risk_score("staging", 5) == 0.4
    # dev x1, 30 days -> 0.0333
    assert scorer.risk_score("dev", 30) == round(1 / 30, 4)


def test_risk_score_clamps_days_at_one():
    # days_left <= 0 must clamp to 1 to avoid div-by-zero / negative.
    assert scorer.risk_score("prod", 0) == 3.0
    assert scorer.risk_score("prod", -5) == 3.0
    assert scorer.risk_score("prod", 1) == 3.0


def test_tier_p1_under_7():
    assert scorer.tier_for(6) == Tier.P1
    assert scorer.tier_for(0) == Tier.P1
    assert scorer.tier_for(-3) == Tier.P1


def test_tier_p2_7_to_30():
    assert scorer.tier_for(7) == Tier.P2
    assert scorer.tier_for(20) == Tier.P2
    assert scorer.tier_for(30) == Tier.P2


def test_tier_p3_31_to_90():
    assert scorer.tier_for(31) == Tier.P3
    assert scorer.tier_for(60) == Tier.P3
    assert scorer.tier_for(90) == Tier.P3


def test_tier_ok_over_90():
    assert scorer.tier_for(91) == Tier.OK
    assert scorer.tier_for(365) == Tier.OK


def test_score_struct():
    sc = scorer.score("prod", 5)
    assert sc.tier == Tier.P1
    assert sc.weight == 3
    assert sc.days_left == 5
    assert sc.risk_score == 0.6
