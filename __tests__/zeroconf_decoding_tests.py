from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from zeroconf import ServiceInfo

from backend.deployment.network_api.utils import (
    decode_zeroconf_hostname,
    decode_zeroconf_properties,
)


def test_decode_zeroconf_properties_decodes_byte_keys_and_values() -> None:
    assert decode_zeroconf_properties(
        {
            b"system_name": b"test",
            b"os_distribution_family": None,
        }
    ) == {
        "system_name": "test",
        "os_distribution_family": None,
    }


def test_decode_zeroconf_hostname_reads_service_info_server() -> None:
    info = ServiceInfo(
        "_watchdog._udp.local.",
        "test._watchdog._udp.local.",
        addresses=[],
        port=9999,
        server="test.local.",
        properties={},
    )

    assert decode_zeroconf_hostname(info) == "test.local."


def test_decode_zeroconf_hostname_decodes_byte_server() -> None:
    info = cast(ServiceInfo, SimpleNamespace(server=b"test.local."))

    assert decode_zeroconf_hostname(info) == "test.local."


def test_decode_zeroconf_hostname_rejects_missing_server() -> None:
    info = cast(ServiceInfo, SimpleNamespace(server=None))

    with pytest.raises(ValueError, match="Missing service server hostname"):
        decode_zeroconf_hostname(info)
