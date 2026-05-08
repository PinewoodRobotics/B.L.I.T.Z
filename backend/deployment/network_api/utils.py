from __future__ import annotations

from collections.abc import Mapping
from dataclasses import MISSING, dataclass, fields
from typing import NewType, TypeVar, get_type_hints

from zeroconf import ServiceInfo


T = TypeVar("T", bound="ZeroconfPropertySchema")
FilePath = NewType("FilePath", str)
FolderPath = NewType("FolderPath", str)


@dataclass
class ZeroconfPropertySchema:
    @classmethod
    def from_zeroconf_properties(
        cls: type[T],
        properties: Mapping[str, str | None],
        **overrides: object,
    ) -> T:
        type_hints = get_type_hints(cls)
        kwargs = dict(overrides)

        for field in fields(cls):
            if not field.init or field.name in kwargs:
                continue

            value = properties.get(field.name)
            if value is None:
                if field.default is not MISSING:
                    kwargs[field.name] = field.default
                    continue
                if field.default_factory is not MISSING:
                    kwargs[field.name] = field.default_factory()
                    continue
                raise ValueError(f"Missing required service property: {field.name}")

            kwargs[field.name] = _coerce_property(
                value, type_hints.get(field.name, field.type)
            )

        return cls(**kwargs)


def _coerce_property(value: str, field_type: object) -> object:
    if field_type is int:
        return int(value)
    if field_type is FilePath:
        return FilePath(value)
    if field_type is FolderPath:
        return FolderPath(value)
    return value


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
