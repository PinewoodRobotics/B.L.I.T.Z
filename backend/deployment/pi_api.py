from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
import time
from typing import Any, Generic, Iterable, TypeVar

from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf

TProcess = TypeVar("TProcess", bound=object)

SERVICE = "_watchdog._udp.local."
DISCOVERY_TIMEOUT = 2.0


@dataclass
class RaspberryPiInfo:
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


@dataclass
class ExpectedZeroconfServiceInfo:
    hostname: str
    system_name: str
    watchdog_port: int
    autobahn_port: int

    raspberry_pi_info: RaspberryPiInfo


def from_service_info_to_dataclass(service: ServiceInfo) -> ExpectedZeroconfServiceInfo:
    raw_properties = service.properties or {}
    properties: dict[str, Any] = {}

    for raw_key, raw_value in raw_properties.items():
        key = raw_key.decode("utf-8")
        value = raw_value.decode("utf-8") if isinstance(raw_value, bytes) else raw_value
        properties[key] = value

    raspberry_pi_payload: dict[str, Any] = {}
    for field_info in dataclasses.fields(RaspberryPiInfo):
        if field_info.name not in properties:
            raise ValueError(f"Missing required service property: {field_info.name}")
        value = properties[field_info.name]
        if field_info.type in (int, "int"):
            value = int(value)
        raspberry_pi_payload[field_info.name] = value

    if service.server is None:
        raise ValueError("Missing service server hostname")
    hostname = (
        service.server.decode("utf-8")
        if isinstance(service.server, bytes)
        else str(service.server)
    )

    return ExpectedZeroconfServiceInfo(
        hostname=hostname,
        system_name=properties["system_name"],
        watchdog_port=int(properties["watchdog_port"]),
        autobahn_port=int(properties["autobahn_port"]),
        raspberry_pi_info=RaspberryPiInfo(**raspberry_pi_payload),
    )


def _process_to_name(p: Any) -> str:
    """
    Converts process identifiers to the string name expected by the watchdog API.

    Supports:
    - strings ("april-server")
    - Enums (uses str(enum_value))
    - _WeightedProcess (uses .get_name() if present, else str(...))
    """

    if p is None:
        raise ValueError("Process cannot be None")

    if isinstance(p, str):
        return p

    get_name = getattr(p, "get_name", None)
    if callable(get_name):
        return str(get_name())

    return str(p)


@dataclass(slots=True)
class RaspberryPi(Generic[TProcess]):
    """
    Unified Raspberry Pi representation with HTTP API and deployment/discovery capabilities.

    Combines:
    - HTTP watchdog API (set_config, start/stop processes)
    - Zeroconf discovery (discover_all)
    - SSH deployment fields (address, password, port)
    """

    general_info: RaspberryPiInfo

    # HTTP API fields
    host: str
    watchdog_port: int
    autobahn_port: int

    # SSH/deployment fields
    password: str = dataclasses.field(default="ubuntu")
    ssh_port: int = dataclasses.field(default=22)

    # Process management
    processes_to_run: list[str] = field(default_factory=list)
    weight: float = 0.0

    @property
    def coms_address(self) -> str:
        return f"http://{self.host}:{self.watchdog_port}"

    def add_process(self, process: TProcess) -> None:
        self.processes_to_run.append(_process_to_name(process))

    def add_processes(self, processes: Iterable[TProcess]) -> None:
        for p in processes:
            self.add_process(p)

    def set_config(self, raw_config_base64: str, *, timeout_s: float = 5.0) -> bool:
        """
        Sends configuration to the Pi.

        Note: existing Python tooling uses {"config": "..."} while the Java code
        uses {"config_base64": "..."}. We send BOTH keys for compatibility.
        """
        import requests

        payload = {"config": raw_config_base64, "config_base64": raw_config_base64}
        r = requests.post(
            f"{self.coms_address}/set/config", json=payload, timeout=timeout_s
        )
        return r.status_code == 200

    def set_processes(
        self,
        process_types: Iterable[TProcess] | None = None,
        *,
        timeout_s: float = 5.0,
    ) -> bool:
        """
        Set the process list on the Pi via POST /set/processes.
        If process_types is provided, also updates self.processes_to_run.
        """
        import requests

        names = (
            [_process_to_name(p) for p in process_types]
            if process_types is not None
            else list(self.processes_to_run)
        )
        payload = {"process_types": names}
        r = requests.post(
            f"{self.coms_address}/set/processes", json=payload, timeout=timeout_s
        )
        if r.status_code != 200:
            return False
        if process_types is not None:
            self.processes_to_run = names
        return True

    def stop_all_set_config_and_start(
        self,
        raw_config_base64: str,
        *,
        new_processes_to_run: Iterable[TProcess] | None = None,
        timeout_s: float = 5.0,
    ) -> bool:
        if not self.set_config(raw_config_base64, timeout_s=timeout_s):
            return False

        return self.set_processes(new_processes_to_run, timeout_s=timeout_s)

    @classmethod
    def _from_zeroconf(cls, service: ServiceInfo):
        """Creates a RaspberryPi instance from a zeroconf ServiceInfo."""
        properties = from_service_info_to_dataclass(service)

        return cls(
            general_info=properties.raspberry_pi_info,
            host=properties.hostname,
            watchdog_port=properties.watchdog_port,
            autobahn_port=properties.autobahn_port,
        )

    @classmethod
    def discover_all(cls):
        """Discovers all Raspberry Pis on the network via zeroconf."""
        raspberrypis: list[RaspberryPi[Any]] = []
        zc = Zeroconf()

        class _Listener(ServiceListener):
            def __init__(self, out: list[RaspberryPi[Any]]):
                self.out: list[RaspberryPi[Any]] = out

            def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                info = zc.get_service_info(type_, name)
                if info is None:
                    return
                try:
                    self.out.append(RaspberryPi._from_zeroconf(info))
                except Exception:
                    pass

            def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                return

            def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                return

        _ = ServiceBrowser(zc, SERVICE, listener=_Listener(raspberrypis))
        time.sleep(DISCOVERY_TIMEOUT)
        zc.close()
        return raspberrypis
