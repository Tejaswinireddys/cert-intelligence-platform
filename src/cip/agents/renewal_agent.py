"""Renewal agent — wraps the DETERMINISTIC engine.renew. Generates/holds no keys.

The agent's only tool is `request_renewal`, which calls the deterministic Venafi
renewal via the engine. The CSR/key is generated at the workload or in Venafi per
the cert's key_handling_policy — never by the agent.
"""
from __future__ import annotations

from cip.agents.tools import registry
from cip.engine import renew as engine_renew
from cip.models import Certificate


@registry.register("request_renewal")
def _request_renewal(*, serial: str, valid_to_iso: str, key_handling_policy: str) -> dict:
    # Delegates to deterministic engine. The agent passes a reference only.
    return engine_renew.request_renewal(
        serial=serial, valid_to_iso=valid_to_iso, key_handling_policy=key_handling_policy
    )


def request_for(cert: Certificate) -> dict:
    """Agent entrypoint: ask the engine to renew. No key ever touches the agent."""
    if cert.key_handling_policy == "agent":  # invariant guard
        raise ValueError("key_handling_policy 'agent' is forbidden")
    return registry.call(
        agent="renewal_agent",
        tool="request_renewal",
        args={
            "serial": cert.serial,
            "valid_to_iso": cert.valid_to.isoformat(),
            "key_handling_policy": cert.key_handling_policy,
        },
    )
