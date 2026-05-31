"""Ownership resolution + confidence.

Confidence is computed deterministically from how many CMDB joins resolved
cleanly: CN/SAN -> service -> server CI -> app CI -> team. When AI suggests an
owner in the 0.50-0.79 band, log the suggestion AND the human's final answer
so systematic AI error can be detected (the accuracy loop).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OwnerResolution(BaseModel):
    serial: str
    owner_group: Optional[str] = None
    escalation_path: Optional[str] = None
    application_ci: Optional[str] = None
    server_ci: Optional[str] = None
    confidence: float = 0.0
    joins_resolved: int = 0  # 0..5 (CN/SAN, service, server CI, app CI, team)
    reason: str = ""  # why this confidence (esp. for orphans)


class AiSuggestion(BaseModel):
    """Accuracy-loop record: AI's suggested owner vs the human's final answer."""

    serial: str
    suggested_owner: str
    confidence: float
    human_final: Optional[str] = None
    correct: Optional[bool] = None  # set when human_final is recorded
    ts: datetime = Field(default_factory=lambda: datetime.utcnow())
