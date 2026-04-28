from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import re
import time

from backend.deployment.compilation.util.systems import (
    Architecture,
    LinuxDistro,
    PythonVersion,
    SystemId,
)
from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf


SERVICE = "_watchdog._udp.local."


@dataclass
class CoprocessorInfo:
    platform_machine: str
    platform_platform: str
    python_version_major: int
    python_version_minor: int
    os_release_id: str | None = None
    os_release_id_like: str | None = None
    os_release_version_id: str | None = None

    @classmethod
    def from_properties(cls, properties: Mapping[str, object]) -> "CoprocessorInfo":
        return cls(
            platform_machine=_str_property(properties, "platform_machine"),
            platform_platform=_str_property(properties, "platform_platform"),
            python_version_major=_int_property(properties, "python_version_major"),
            python_version_minor=_int_property(properties, "python_version_minor"),
            os_release_id=_optional_str_property(properties, "os_release_id"),
            os_release_id_like=_optional_str_property(
                properties,
                "os_release_id_like",
            ),
            os_release_version_id=_optional_str_property(
                properties,
                "os_release_version_id",
            ),
        )


@dataclass
class DiscoveredNetworkSystem:
    hostname: str  # EG: "nathan-hale.local"
    system_name: str  # EG: "nathan-hale"
    watchdog_port: int  # EG: 9999
    autobahn_port: int  # EG: 9999

    blitz_path: str  # EG: "/opt/blitz/B.L.I.T.Z"

    coprocessor_info: CoprocessorInfo

    @classmethod
    def from_service_info(cls, info: ServiceInfo) -> "DiscoveredNetworkSystem":
        properties = _decode_properties(info.properties) if info.properties else {}

        return cls(
            hostname=_decode_hostname(info),
            system_name=_str_property(properties, "system_name"),
            watchdog_port=_int_property(properties, "watchdog_port"),
            autobahn_port=_int_property(properties, "autobahn_port"),
            blitz_path=_str_property(properties, "blitz_path"),
            coprocessor_info=CoprocessorInfo.from_properties(properties),
        )

    def __hash__(self) -> int:
        return hash(self.hostname)

    def system_id_diagnostics(self) -> dict[str, object]:
        info = self.coprocessor_info
        return {
            "hostname": self.hostname,
            "system_name": self.system_name,
            "watchdog_port": self.watchdog_port,
            "autobahn_port": self.autobahn_port,
            "blitz_path": self.blitz_path,
            "platform_text": self._platform_text(),
            "platform_machine": info.platform_machine,
            "platform_platform": info.platform_platform,
            "os_release_id": info.os_release_id,
            "os_release_id_like": info.os_release_id_like,
            "os_release_version_id": info.os_release_version_id,
        }

    def _platform_text(self) -> str:
        info = self.coprocessor_info
        return " ".join(
            value
            for value in [
                info.platform_platform,
                info.os_release_id,
                info.os_release_id_like,
                info.os_release_version_id,
            ]
            if value
        ).lower()

    def _system_id_error(self, message: str) -> ValueError:
        diagnostics = "; ".join(
            f"{key}={value!r}" for key, value in self.system_id_diagnostics().items()
        )
        return ValueError(f"{message} for {self.hostname}. diagnostics: {diagnostics}")

    def to_system_id(self) -> SystemId:
        info = self.coprocessor_info
        platform_text = self._platform_text()
        glibc_match = re.search(r"glibc(?P<version>\d+(?:\.\d+)*)", platform_text)
        if glibc_match is None:
            raise self._system_id_error("Could not infer glibc version")
        glibc_version = glibc_match.group("version")

        try:
            architecture = Architecture.from_machine(info.platform_machine)
        except ValueError as error:
            raise self._system_id_error(str(error)) from error

        try:
            linux_distro = LinuxDistro.from_os_release(
                os_id=info.os_release_id,
                os_id_like=info.os_release_id_like,
                version_id=info.os_release_version_id,
                platform_text=platform_text,
            )
        except ValueError as error:
            raise self._system_id_error(str(error)) from error

        return SystemId(
            c_lib_version=glibc_version,
            linux_distro=linux_distro,
            architecture=architecture,
            python_version=PythonVersion(
                major=info.python_version_major,
                minor=info.python_version_minor,
            ),
        )


def _decode_properties(properties: Mapping[bytes, bytes | None]) -> dict[str, object]:
    return {key.decode("utf-8"): _decode(value) for key, value in properties.items()}


def _decode(value: bytes | None) -> str | None:
    return value.decode("utf-8") if value is not None else None


def _decode_hostname(info: ServiceInfo) -> str:
    if info.server is None:
        raise ValueError("Missing service server hostname")
    if isinstance(info.server, bytes):
        return info.server.decode("utf-8")
    return info.server


def _property(properties: Mapping[str, object], field_name: str) -> object:
    value = properties.get(field_name)
    if value is None:
        raise ValueError(f"Missing required service property: {field_name}")
    return value


def _str_property(properties: Mapping[str, object], field_name: str) -> str:
    return str(_property(properties, field_name))


def _int_property(properties: Mapping[str, object], field_name: str) -> int:
    return int(str(_property(properties, field_name)))


def _optional_str_property(
    properties: Mapping[str, object], field_name: str
) -> str | None:
    value = properties.get(field_name)
    return None if value is None else str(value)


def discover_all_on_network(
    timeout_seconds: float = 5.0,
    on_discovered: Callable[[DiscoveredNetworkSystem], None] | None = None,
    on_tick: Callable[[float], None] | None = None,
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
                already_discovered = discovered in self.out
                self.out.add(discovered)
                if on_discovered is not None and not already_discovered:
                    on_discovered(discovered)
            except Exception:
                pass

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            return

        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            return

    _ = ServiceBrowser(zc, SERVICE, listener=_Listener(discovered_zerocofs))
    end_time = time.monotonic() + timeout_seconds
    while True:
        remaining_seconds = max(0.0, end_time - time.monotonic())
        if on_tick is not None:
            on_tick(remaining_seconds)
        if remaining_seconds <= 0:
            break
        time.sleep(min(0.2, remaining_seconds))

    zc.close()
    return discovered_zerocofs
