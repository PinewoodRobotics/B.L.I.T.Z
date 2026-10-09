from __future__ import annotations

from dataclasses import dataclass, fields
from collections.abc import Sequence
import re
import time
from urllib.parse import urlsplit
import warnings

import requests

from backend.deployment.compilation.util.systems import (
    Architecture,
    LinuxDistro,
    PythonVersion,
    SystemId,
)
from backend.deployment.network_api.utils import (
    FolderPath,
    ZeroconfPropertySchema,
    decode_zeroconf_hostname,
    decode_zeroconf_properties,
)
from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf


SERVICE = "_watchdog._udp.local."


@dataclass
class DiscoveredNetworkSystem(ZeroconfPropertySchema):
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

    @classmethod
    def from_service_info(cls, info: ServiceInfo) -> "DiscoveredNetworkSystem":
        return cls.from_zeroconf_properties(
            decode_zeroconf_properties(info.properties),
            hostname=decode_zeroconf_hostname(info),
        )

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
        return hash(self.hostname)


def discover_at_addresses(addresses: Sequence[str]) -> set[DiscoveredNetworkSystem]:
    """Query specific watchdogs directly when multicast discovery is unavailable."""
    discovered: set[DiscoveredNetworkSystem] = set()
    for address in addresses:
        if "://" in address:
            raise ValueError(f"Use HOST:PORT for --device, without a URL scheme: {address}")
        parsed = urlsplit(f"//{address}")
        try:
            port = parsed.port
        except ValueError as error:
            raise ValueError(f"Invalid --device address: {address}") from error
        if (
            not parsed.hostname or port is None or parsed.path or parsed.query
            or parsed.fragment or parsed.username or parsed.password
        ):
            raise ValueError(f"Use HOST:PORT for --device: {address}")
        try:
            response = requests.get(
                f"http://{address}/get/system/identity", timeout=5
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as error:
            raise ValueError(f"Could not query watchdog at {address}: {error}") from error
        except ValueError as error:
            raise ValueError(f"Invalid watchdog identity from {address}") from error
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid watchdog identity from {address}")
        properties = {
            str(key): str(value) if value is not None else None
            for key, value in payload.items()
        }
        system = DiscoveredNetworkSystem.from_zeroconf_properties(
            properties, hostname=parsed.hostname
        )
        system.watchdog_port = port
        discovered.add(system)
    return discovered


def discover_all_on_network(
    timeout_seconds: float = 5.0,
) -> set[DiscoveredNetworkSystem]:
    discovered_zerocofs: set[DiscoveredNetworkSystem] = set()
    zc = Zeroconf()

    class _Listener(ServiceListener):
        def __init__(self, out: set[DiscoveredNetworkSystem]):
            self.out: set[DiscoveredNetworkSystem] = out

        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            if info is None:
                return
            try:
                discovered = DiscoveredNetworkSystem.from_service_info(info)
                self.out.add(discovered)
            except Exception as error:
                warnings.warn(
                    f"Ignoring invalid watchdog service {name}: {error}",
                    RuntimeWarning,
                    stacklevel=2,
                )

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            return

        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            return

    _ = ServiceBrowser(zc, SERVICE, listener=_Listener(discovered_zerocofs))
    time.sleep(timeout_seconds)
    zc.close()

    return discovered_zerocofs
