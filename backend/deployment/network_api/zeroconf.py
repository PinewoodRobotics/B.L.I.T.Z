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
    os_name: str
    sys_platform: str
    platform_system: str
    platform_release: str
    platform_version: str
    platform_machine: str
    platform_platform: str
    python_executable: str
    python_version: str
    python_version_major: int
    python_version_minor: int
    python_version_micro: int
    python_implementation: str
    implementation_short: str
    abi_guess: str | None
    sys_abiflags: str
    soabi: str | None
    ext_suffix: str | None
    pip_version: str
    os_release_pretty_name: str | None = None
    os_release_name: str | None = None
    os_release_id: str | None = None
    os_release_id_like: str | None = None
    os_release_version: str | None = None
    os_release_version_id: str | None = None
    os_release_version_codename: str | None = None

    @classmethod
    def from_properties(cls, properties: Mapping[str, object]) -> "CoprocessorInfo":
        return cls(
            os_name=_str_property(properties, "os_name"),
            sys_platform=_str_property(properties, "sys_platform"),
            platform_system=_str_property(properties, "platform_system"),
            platform_release=_str_property(properties, "platform_release"),
            platform_version=_str_property(properties, "platform_version"),
            platform_machine=_str_property(properties, "platform_machine"),
            platform_platform=_str_property(properties, "platform_platform"),
            python_executable=_str_property(properties, "python_executable"),
            python_version=_str_property(properties, "python_version"),
            python_version_major=_int_property(properties, "python_version_major"),
            python_version_minor=_int_property(properties, "python_version_minor"),
            python_version_micro=_int_property(properties, "python_version_micro"),
            python_implementation=_str_property(properties, "python_implementation"),
            implementation_short=_str_property(properties, "implementation_short"),
            abi_guess=_optional_str_property(properties, "abi_guess"),
            sys_abiflags=_str_property(properties, "sys_abiflags"),
            soabi=_optional_str_property(properties, "soabi"),
            ext_suffix=_optional_str_property(properties, "ext_suffix"),
            pip_version=_str_property(properties, "pip_version"),
            os_release_pretty_name=_optional_str_property(
                properties,
                "os_release_pretty_name",
            ),
            os_release_name=_optional_str_property(properties, "os_release_name"),
            os_release_id=_optional_str_property(properties, "os_release_id"),
            os_release_id_like=_optional_str_property(
                properties,
                "os_release_id_like",
            ),
            os_release_version=_optional_str_property(
                properties,
                "os_release_version",
            ),
            os_release_version_id=_optional_str_property(
                properties,
                "os_release_version_id",
            ),
            os_release_version_codename=_optional_str_property(
                properties,
                "os_release_version_codename",
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
            "os_name": info.os_name,
            "sys_platform": info.sys_platform,
            "platform_system": info.platform_system,
            "platform_release": info.platform_release,
            "platform_version": info.platform_version,
            "platform_machine": info.platform_machine,
            "platform_platform": info.platform_platform,
            "python_executable": info.python_executable,
            "python_version": info.python_version,
            "python_implementation": info.python_implementation,
            "implementation_short": info.implementation_short,
            "abi_guess": info.abi_guess,
            "sys_abiflags": info.sys_abiflags,
            "soabi": info.soabi,
            "ext_suffix": info.ext_suffix,
            "pip_version": info.pip_version,
            "os_release_pretty_name": info.os_release_pretty_name,
            "os_release_name": info.os_release_name,
            "os_release_id": info.os_release_id,
            "os_release_id_like": info.os_release_id_like,
            "os_release_version": info.os_release_version,
            "os_release_version_id": info.os_release_version_id,
            "os_release_version_codename": info.os_release_version_codename,
        }

    def _platform_text(self) -> str:
        info = self.coprocessor_info
        return " ".join(
            value
            for value in [
                info.platform_platform,
                info.platform_version,
                info.platform_release,
                info.os_release_pretty_name,
                info.os_release_name,
                info.os_release_id,
                info.os_release_id_like,
                info.os_release_version,
                info.os_release_version_id,
                info.os_release_version_codename,
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

        architecture_by_machine = {
            "aarch64": Architecture.AARCH64,
            "arm64": Architecture.AARCH64,
            "x86_64": Architecture.AMD64,
            "amd64": Architecture.AMD64,
            "armv7l": Architecture.ARM32,
            "armv7": Architecture.ARM32,
            "armhf": Architecture.ARM32,
        }
        linux_distro_by_text = {
            "24.04": LinuxDistro.UBUNTU_24,
            "24-04": LinuxDistro.UBUNTU_24,
            "noble": LinuxDistro.UBUNTU_24,
            "22.04": LinuxDistro.UBUNTU_22,
            "22-04": LinuxDistro.UBUNTU_22,
            "jammy": LinuxDistro.UBUNTU_22,
            "20.04": LinuxDistro.UBUNTU_20,
            "20-04": LinuxDistro.UBUNTU_20,
            "focal": LinuxDistro.UBUNTU_20,
            "bookworm": LinuxDistro.DEBIAN_12,
            "bullseye": LinuxDistro.DEBIAN_11,
        }

        architecture = architecture_by_machine.get(info.platform_machine.lower())
        if architecture is None:
            raise self._system_id_error(
                f"Unsupported architecture from zeroconf: {info.platform_machine}"
            )

        linux_distro = next(
            (
                distro
                for marker, distro in linux_distro_by_text.items()
                if marker in platform_text
            ),
            LinuxDistro.UBUNTU_24 if "ubuntu" in platform_text else None,
        )
        if (
            linux_distro is None
            and self.system_name == "blitz-discoverable-dev-test"
            and "linuxkit" in platform_text
            and glibc_version == "2.39"
        ):
            linux_distro = LinuxDistro.UBUNTU_24
        if linux_distro is None:
            raise self._system_id_error("Could not infer Linux distro")

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
