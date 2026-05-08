from __future__ import annotations

import pytest
from zeroconf import ServiceInfo

from backend.deployment.network_api.utils import FolderPath
from backend.deployment.network_api.zeroconf import DiscoveredNetworkSystem


def _service_info(properties: dict[str, object]) -> ServiceInfo:
    return ServiceInfo(
        "_watchdog._udp.local.",
        "test._watchdog._udp.local.",
        addresses=[],
        port=9999,
        server="test.local.",
        properties=properties,
    )


def test_discovered_network_system_parses_current_zeroconf_properties() -> None:
    system = DiscoveredNetworkSystem.from_service_info(
        _service_info(
            {
                "system_name": "test",
                "watchdog_port": "9999",
                "autobahn_port": "9998",
                "blitz_path": "/opt/blitz",
                "machine_architecture": "aarch64",
                "platform_description": "Linux-6.8.0-glibc2.39-aarch64",
                "python_major_version": "3",
                "python_minor_version": "12",
                "os_distribution_id": "ubuntu",
                "os_distribution_family": None,
                "os_distribution_version_id": "24.04",
            }
        )
    )

    assert system.hostname == "test.local."
    assert system.system_name == "test"
    assert system.watchdog_port == 9999
    assert system.autobahn_port == 9998
    assert system.blitz_path == FolderPath("/opt/blitz")
    assert system.machine_architecture == "aarch64"
    assert system.python_major_version == 3
    assert system.python_minor_version == 12
    assert system.os_distribution_family is None


def test_discovered_network_system_requires_current_zeroconf_properties() -> None:
    with pytest.raises(
        ValueError, match="Missing required service property: machine_architecture"
    ):
        DiscoveredNetworkSystem.from_service_info(
            _service_info(
                {
                    "system_name": "test",
                    "watchdog_port": "9999",
                    "autobahn_port": "9998",
                    "blitz_path": "/opt/blitz",
                    "platform_machine": "aarch64",
                    "platform_description": "Linux-6.8.0-glibc2.39-aarch64",
                    "python_major_version": "3",
                    "python_minor_version": "12",
                }
            )
        )
