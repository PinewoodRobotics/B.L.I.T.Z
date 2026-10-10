from __future__ import annotations

import socket

import pytest
from zeroconf import ServiceInfo

from backend.deployment.network_api.zeroconf import DiscoveredEndpoint, SERVICE


def _service_info(properties: dict[str, object]) -> ServiceInfo:
    return ServiceInfo(
        SERVICE, "test." + SERVICE,
        addresses=[socket.inet_aton("192.0.2.10")], port=5000,
        server="server-alias.local.", properties=properties,
    )


def properties():
    return {"schema_version": "2", "hostname": "test.local", "system_name": "test", "watchdog_port": "5000", "autobahn_port": "8080", "ssh_port": "2200"}


def test_endpoint_parses_connection_metadata_without_system_profile():
    endpoint = DiscoveredEndpoint.from_service_info(_service_info(properties()))
    assert endpoint.hostname == "test.local"
    assert endpoint.contact_host == "192.0.2.10"
    assert endpoint.watchdog_port == 5000
    assert endpoint.autobahn_port == 8080
    assert endpoint.ssh_port == 2200
    assert endpoint.aliases == ("server-alias.local.",)
    assert endpoint.is_blacklisted(["SERVER-ALIAS.LOCAL"])


@pytest.mark.parametrize("field", ["schema_version", "hostname", "system_name", "watchdog_port", "autobahn_port", "ssh_port"])
def test_endpoint_rejects_missing_required_connection_metadata(field):
    payload = properties()
    payload.pop(field)
    with pytest.raises(ValueError, match="incompatible|Missing required discovery property"):
        DiscoveredEndpoint.from_service_info(_service_info(payload))


def test_old_full_profile_advertisement_is_incompatible():
    payload = properties()
    payload.pop("schema_version")
    payload["machine_architecture"] = "aarch64"
    with pytest.raises(ValueError, match="upgrade watchdog and deployer"):
        DiscoveredEndpoint.from_service_info(_service_info(payload))
