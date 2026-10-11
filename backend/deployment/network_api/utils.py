from __future__ import annotations

from collections.abc import Mapping
from typing import NewType

from zeroconf import ServiceInfo


FilePath = NewType("FilePath", str)
FolderPath = NewType("FolderPath", str)


def decode_zeroconf_properties(
    properties: Mapping[bytes, bytes | None],
) -> dict[str, str | None]:
    return {key.decode("utf-8"): _decode(value) for key, value in properties.items()}


def decode_zeroconf_hostname(info: ServiceInfo) -> str:
    if info.server is None:
        raise ValueError("Missing service server hostname")
    if isinstance(info.server, bytes):
        return info.server.decode("utf-8")
    return info.server


def _decode(value: bytes | None) -> str | None:
    return value.decode("utf-8") if value is not None else None
