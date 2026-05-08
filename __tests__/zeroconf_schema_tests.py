from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import cast

import pytest
from zeroconf import ServiceInfo

from backend.deployment.network_api.utils import (
    FilePath,
    FolderPath,
    ZeroconfPropertySchema,
    decode_zeroconf_hostname,
    decode_zeroconf_properties,
)


@dataclass
class SampleSchema(ZeroconfPropertySchema):
    name: str
    port: int
    file_path: FilePath = FilePath("default.txt")
    folder_path: FolderPath = FolderPath("default/")
    optional_name: str | None = None
    label: str = "default-label"
    tags: list[str] = field(default_factory=list)
    derived: str = field(init=False, default="derived-value")


def test_schema_reads_dataclass_fields_and_coerces_ints() -> None:
    parsed = SampleSchema.from_zeroconf_properties(
        {
            "name": "watchdog",
            "port": "9999",
            "file_path": "deploy.py",
            "folder_path": "backend/",
            "optional_name": "pi-one",
            "label": "custom-label",
        }
    )

    assert parsed == SampleSchema(
        name="watchdog",
        port=9999,
        file_path=FilePath("deploy.py"),
        folder_path=FolderPath("backend/"),
        optional_name="pi-one",
        label="custom-label",
    )
    assert parsed.tags == []
    assert parsed.derived == "derived-value"


def test_schema_uses_dataclass_defaults_for_missing_optional_fields() -> None:
    parsed = SampleSchema.from_zeroconf_properties(
        {
            "name": "watchdog",
            "port": "9999",
        }
    )

    assert parsed.optional_name is None
    assert parsed.label == "default-label"
    assert parsed.tags == []


def test_schema_default_factory_gets_fresh_values() -> None:
    first = SampleSchema.from_zeroconf_properties({"name": "one", "port": "1"})
    second = SampleSchema.from_zeroconf_properties({"name": "two", "port": "2"})

    first.tags.append("mutated")

    assert second.tags == []


def test_schema_overrides_skip_property_lookup_and_coercion() -> None:
    parsed = SampleSchema.from_zeroconf_properties(
        {"port": "9999"},
        name="override-name",
        port=1234,
    )

    assert parsed.name == "override-name"
    assert parsed.port == 1234


def test_schema_rejects_missing_required_fields() -> None:
    with pytest.raises(ValueError, match="Missing required service property: name"):
        SampleSchema.from_zeroconf_properties({"port": "9999"})


def test_schema_treats_none_required_values_as_missing() -> None:
    with pytest.raises(ValueError, match="Missing required service property: name"):
        SampleSchema.from_zeroconf_properties({"name": None, "port": "9999"})


def test_schema_preserves_none_for_optional_fields() -> None:
    parsed = SampleSchema.from_zeroconf_properties(
        {
            "name": "watchdog",
            "port": "9999",
            "optional_name": None,
        }
    )

    assert parsed.optional_name is None


def test_schema_surfaces_invalid_int_values() -> None:
    with pytest.raises(ValueError, match="invalid literal"):
        SampleSchema.from_zeroconf_properties(
            {
                "name": "watchdog",
                "port": "not-a-port",
            }
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
