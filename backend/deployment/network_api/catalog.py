"""The shared BLITZ HTTP catalog contract used by targets and deployment clients."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, fields
import re
from typing import Any

from backend.deployment.compilation.util.systems import Architecture, LinuxDistro, PythonVersion, SystemId
from backend.deployment.network_api.utils import FolderPath

CATALOG_SCHEMA_VERSION = 3

@dataclass
class SystemCatalog:
    hostname: str  # EG: "nathan-hale.local"
    system_name: str  # EG: "nathan-hale"
    watchdog_port: int  # EG: 9999
    autobahn_port: int  # EG: 9999

    blitz_path: FolderPath  # EG: "/opt/blitz/B.L.I.T.Z"

    machine_architecture: str
    platform_description: str
    python_major_version: int
    python_minor_version: int
    os_distribution_id: str | None = None
    os_distribution_family: str | None = None
    os_distribution_version_id: str | None = None
    capabilities: dict[str, str] = field(default_factory=dict)
    ssh_port: int = 22
    watchdog_host: str | None = None
    autobahn_host: str | None = None
    ssh_host: str | None = None

    def _platform_text(self) -> str:
        return " ".join(
            value
            for value in [
                self.platform_description,
                self.os_distribution_id,
                self.os_distribution_family,
                self.os_distribution_version_id,
            ]
            if value
        ).lower()

    def to_system_id(self) -> SystemId:
        platform_text = self._platform_text()
        glibc_match = re.search(r"glibc(?P<version>\d+(?:\.\d+)*)", platform_text)
        if glibc_match is None:
            raise ValueError("Could not infer glibc version: " + str(self))

        glibc_version = glibc_match.group("version")

        try:
            architecture = Architecture.from_machine(self.machine_architecture)
        except ValueError as error:
            raise ValueError(str(error) + " for " + str(self)) from error

        try:
            linux_distro = LinuxDistro.from_os_release(
                os_id=self.os_distribution_id,
                os_id_like=self.os_distribution_family,
                version_id=self.os_distribution_version_id,
                platform_text=platform_text,
            )
        except ValueError as error:
            raise ValueError(str(error) + " for " + str(self)) from error

        return SystemId(
            capabilities=tuple(sorted(self.capabilities.items())),
            c_lib_version=glibc_version,
            linux_distro=linux_distro,
            architecture=architecture,
            python_version=PythonVersion(
                major=self.python_major_version,
                minor=self.python_minor_version,
            ),
        )

    def __str__(self) -> str:
        lines: list[str] = []
        for field in fields(self):
            value = getattr(self, field.name)
            if value is not None:
                lines.append(f"{field.name}: {value}")
        return "\n".join(lines)

    def __hash__(self) -> int:
        return hash((self.watchdog_host or self.hostname, self.watchdog_port))


    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_payload(self) -> dict[str, Any]:
        return {"schema_version": CATALOG_SCHEMA_VERSION, "system": self.to_dict()}

    @classmethod
    def from_payload(cls, payload: object) -> SystemCatalog:
        """Validate native JSON types without a text-property round trip."""
        if not isinstance(payload, Mapping) or type(payload.get("schema_version")) is not int or payload.get("schema_version") != CATALOG_SCHEMA_VERSION or not isinstance(payload.get("system"), Mapping):
            raise ValueError(f"Incompatible watchdog catalog; expected schema_version={CATALOG_SCHEMA_VERSION}. Upgrade watchdog and deployer together.")
        profile = payload["system"]
        required = ("hostname", "system_name", "blitz_path", "machine_architecture", "platform_description", "capabilities", "python_major_version", "python_minor_version", "watchdog_port", "autobahn_port", "ssh_port")
        for name in required:
            if name not in profile or profile[name] is None:
                raise ValueError(f"Missing required catalog field: {name}")
        for name in ("hostname", "system_name", "blitz_path", "machine_architecture", "platform_description"):
            if not isinstance(profile[name], str) or not profile[name].strip():
                raise ValueError(f"Invalid catalog field: {name}")
        for name in ("python_major_version", "python_minor_version"):
            if type(profile[name]) is not int or profile[name] < 0:
                raise ValueError(f"Invalid catalog field: {name}")
        for name in ("watchdog_port", "autobahn_port", "ssh_port"):
            if type(profile[name]) is not int or not 1 <= profile[name] <= 65535:
                raise ValueError(f"Invalid catalog field: {name}")
        for name in ("hostname", "watchdog_host", "autobahn_host", "ssh_host"):
            host = profile.get(name)
            if host is not None and (not isinstance(host, str) or not host.strip() or any(character in host for character in "/\\?#@[]") or any(character.isspace() for character in host)):
                raise ValueError(f"Invalid catalog field: {name}")
        for name in ("os_distribution_id", "os_distribution_family", "os_distribution_version_id"):
            value = profile.get(name)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"Invalid catalog field: {name}")
        capabilities = profile["capabilities"]
        if not isinstance(capabilities, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in capabilities.items()):
            raise ValueError("Invalid capabilities")
        values = {item.name: profile[item.name] for item in fields(cls) if item.name in profile}
        values["capabilities"] = dict(capabilities)
        system = cls(**values)
        system.to_system_id()
        return system
