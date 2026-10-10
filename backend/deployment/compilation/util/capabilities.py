"""Supported target capabilities and their wire-format contracts.

Add capabilities here with a defined meaning and detector family. Distribution
profiles select candidate families; they never prove hardware is available.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
import re
from types import MappingProxyType


class Capability(str, Enum):
    CUDA = "cuda"
    NVIDIA_DRIVER = "nvidia_driver"
    V4L2 = "v4l2"
    I2C = "i2c"
    SPI = "spi"
    GPIO = "gpio"

    @classmethod
    def from_name(cls, name: str | Capability) -> Capability:
        try:
            return cls(name)
        except (ValueError, TypeError) as error:
            raise ValueError(f"Unsupported capability: {name!r}") from error


class CapabilityDetectorFamily(str, Enum):
    NVIDIA = "nvidia"
    LINUX_DEVICE_INTERFACES = "linux_device_interfaces"


@dataclass(frozen=True)
class CapabilityDefinition:
    family: CapabilityDetectorFamily
    description: str
    versioned: bool = False


CAPABILITY_DEFINITIONS: Mapping[Capability, CapabilityDefinition] = MappingProxyType({
    Capability.CUDA: CapabilityDefinition(
        CapabilityDetectorFamily.NVIDIA,
        "CUDA driver support reported for an accessible NVIDIA GPU by nvidia-smi or the initialized driver API; not an installed toolkit.",
        versioned=True,
    ),
    Capability.NVIDIA_DRIVER: CapabilityDefinition(
        CapabilityDetectorFamily.NVIDIA,
        "Driver version reported by nvidia-smi for an accessible NVIDIA GPU.",
        versioned=True,
    ),
    Capability.V4L2: CapabilityDefinition(
        CapabilityDetectorFamily.LINUX_DEVICE_INTERFACES,
        "At least one readable/writable /dev/videoN character device; no camera or codec guarantee.",
    ),
    Capability.I2C: CapabilityDefinition(
        CapabilityDetectorFamily.LINUX_DEVICE_INTERFACES,
        "At least one readable/writable /dev/i2c-N character device; no attached peripheral guarantee.",
    ),
    Capability.SPI: CapabilityDefinition(
        CapabilityDetectorFamily.LINUX_DEVICE_INTERFACES,
        "At least one readable/writable /dev/spidevN.N character device; no attached peripheral guarantee.",
    ),
    Capability.GPIO: CapabilityDefinition(
        CapabilityDetectorFamily.LINUX_DEVICE_INTERFACES,
        "At least one readable/writable /dev/gpiochipN character device; no pin availability guarantee.",
    ),
})

LINUX_CAPABILITY_FAMILIES = (
    CapabilityDetectorFamily.LINUX_DEVICE_INTERFACES,
    CapabilityDetectorFamily.NVIDIA,
)
PRESENCE_VALUE = "present"


def validate_capability_version(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d+(\.\d+)*", value):
        raise ValueError(f"Invalid capability version: {value!r}")
    return value


def normalize_capabilities(
    values: Mapping[str | Capability, str] | Iterable[tuple[str | Capability, str]],
) -> dict[str, str]:
    """Validate HTTP catalogs, build plans, and cached profiles identically."""
    if isinstance(values, (str, bytes)):
        raise ValueError("Capabilities must be a mapping or name/value pairs")
    entries = values.items() if isinstance(values, Mapping) else values
    normalized: dict[str, str] = {}
    try:
        for name, value in entries:
            capability = Capability.from_name(name)
            if capability.value in normalized:
                raise ValueError(f"Duplicate target capability: {capability.value}")
            definition = CAPABILITY_DEFINITIONS[capability]
            if definition.versioned:
                validate_capability_version(value)
            elif value != PRESENCE_VALUE:
                raise ValueError(f"Capability {capability.value} requires {PRESENCE_VALUE!r}, got {value!r}")
            normalized[capability.value] = value
    except (TypeError, AttributeError) as error:
        raise ValueError("Capabilities must be a mapping or name/value pairs") from error
    return dict(sorted(normalized.items()))
