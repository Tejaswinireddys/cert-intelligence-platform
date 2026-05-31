"""CMDB agent — CI updates, cert->server link. Never invents owners."""
from __future__ import annotations

from cip.agents.tools import registry
from cip.integrations.cmdb import get_cmdb
from cip.models import Certificate


@registry.register("update_ci")
def _update_ci(*, server_ci: str, fields: dict) -> dict:
    return get_cmdb().update_ci(server_ci=server_ci, fields=fields)


@registry.register("link_cert_to_server")
def _link(*, server_ci: str, serial: str, common_name: str) -> dict:
    return get_cmdb().update_ci(
        server_ci=server_ci, fields={"linked_cert_serial": serial, "linked_cert_cn": common_name}
    )


def sync_after_deploy(cert: Certificate, *, new_serial: str) -> dict:
    """Update the CI: link cert->server, write owner/CA/policy. Closes the loop."""
    if not cert.server_ci:
        return {"skipped": "no server_ci"}
    registry.call(agent="cmdb_agent", tool="link_cert_to_server",
                 args={"server_ci": cert.server_ci, "serial": new_serial,
                       "common_name": cert.common_name})
    return registry.call(agent="cmdb_agent", tool="update_ci",
                        args={"server_ci": cert.server_ci,
                              "fields": {"owner_group": cert.owner_group, "ca": cert.ca,
                                         "key_handling_policy": cert.key_handling_policy}})
