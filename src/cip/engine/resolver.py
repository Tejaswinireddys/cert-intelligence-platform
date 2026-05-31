"""Owner resolver — deterministic CMDB lookup -> owner + confidence.

Confidence is computed from how many CMDB joins resolved cleanly:
    CN/SAN -> service -> server CI -> app CI -> team   (5 joins, 0.20 each)

No LLM here. The AI agent only *suggests* an owner later in the 0.50-0.79 band.
"""
from __future__ import annotations

from cip.integrations.cmdb import get_cmdb
from cip.models import Certificate, route
from cip.models.owner import OwnerResolution

# Each successful join contributes to confidence.
_JOIN_WEIGHT = 0.20


def resolve(cert: Certificate) -> OwnerResolution:
    """Resolve ownership deterministically via the CMDB adapter."""
    cmdb = get_cmdb()
    record = cmdb.lookup(common_name=cert.common_name, sans=cert.sans)

    joins = 0
    reasons: list[str] = []

    # Join 1: CN/SAN matched a CMDB service record at all.
    if record is not None:
        joins += 1
    else:
        return OwnerResolution(
            serial=cert.serial,
            confidence=0.0,
            joins_resolved=0,
            reason="no CMDB CI match for CN/SAN",
        )

    # Join 2: service resolved.
    if record.get("service"):
        joins += 1
    else:
        reasons.append("service unresolved")

    # Join 3: server CI present.
    server_ci = record.get("server_ci") or cert.server_ci
    if server_ci:
        joins += 1
    else:
        reasons.append("no server CI")

    # Join 4: application CI present.
    app_ci = record.get("application_ci") or cert.application_ci
    if app_ci:
        joins += 1
    else:
        reasons.append("no application CI")

    # Join 5: team / owner group present.
    owner_group = record.get("owner_group") or cert.owner_group
    if owner_group:
        joins += 1
    else:
        reasons.append("no owning team")

    confidence = round(joins * _JOIN_WEIGHT, 2)
    reason = "clean resolution" if not reasons else "; ".join(reasons)

    return OwnerResolution(
        serial=cert.serial,
        owner_group=owner_group,
        escalation_path=record.get("escalation_path") or cert.escalation_path,
        application_ci=app_ci,
        server_ci=server_ci,
        confidence=confidence,
        joins_resolved=joins,
        reason=reason,
    )


def routing_for(confidence: float):
    return route(confidence)
