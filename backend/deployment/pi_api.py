from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
import time
from typing import Any, Generic, Iterable, TypeVar

from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf

TProcess = TypeVar("TProcess", bound=object)

SERVICE = "_watchdog._udp.local."
DISCOVERY_TIMEOUT = 2.0


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

    # HTTP API fields
    host: str
    port_coms: int = 5000
    port_autobahn: int | None = None

    # SSH/deployment fields
    address: str | None = None
    password: str = dataclasses.field(default="ubuntu")
    ssh_port: int = dataclasses.field(default=22)

    # Process management
    processes_to_run: list[str] = field(default_factory=list)
    weight: float = 0.0

    def __post_init__(self):
        """If address not set, default to host (common case)."""
        if self.address is None:
            object.__setattr__(self, "address", self.host)

    @property
    def coms_address(self) -> str:
        return f"http://{self.host}:{self.port_coms}"

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

        if new_processes_to_run is None:
            return True

        return self.set_processes(new_processes_to_run, timeout_s=timeout_s)

    @classmethod
    def _from_zeroconf(cls, service: ServiceInfo):
        """Creates a RaspberryPi instance from a zeroconf ServiceInfo."""
        properties = {
            k.decode("utf-8") if isinstance(k, bytes) else k: (
                v.decode("utf-8") if isinstance(v, bytes) else v
            )
            for k, v in (service.properties or {}).items()
        }

        address = (
            (properties.get("hostname_local") or "").rstrip(".")
            or (service.server or "").rstrip(".")
            or None
        )

        if not address:
            raise ValueError("Cannot extract Pi address from zeroconf ServiceInfo")

        return cls(host=address, address=address)

    @classmethod
    def discover_all(cls):
        """Discovers all Raspberry Pis on the network via zeroconf."""
        raspberrypis: list[RaspberryPi] = []
        zc = Zeroconf()

        class _Listener(ServiceListener):
            def __init__(self, out: list[RaspberryPi]):
                self.out: list[RaspberryPi] = out

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


'''
def start_processes(self, *, timeout_s: float = 5.0) -> bool:
        if not self.processes_to_run:
            return False
        import requests

        payload = {"process_types": list(self.processes_to_run)}
        r = requests.post(
            f"{self.coms_address}/start/process", json=payload, timeout=timeout_s
        )
        return r.status_code == 200

    def stop_processes(self, *, timeout_s: float = 5.0) -> bool:
        import requests

        payload = {"process_types": list(self.processes_to_run)}
        r = requests.post(
            f"{self.coms_address}/stop/process", json=payload, timeout=timeout_s
        )
        return r.status_code == 200

    def stop_all_processes(self, *, timeout_s: float = 5.0) -> bool:
        """
        Stops all processes on the Pi (calls /stop/all/processes endpoint).
        This is more aggressive than stop_processes() which only stops known processes.
        """
        import requests

        r = requests.post(f"{self.coms_address}/stop/all/processes", timeout=timeout_s)
        return r.status_code == 200

    def stop_process(self, process: TProcess, *, timeout_s: float = 5.0) -> bool:
        """
        Stops a specific process and removes it from the local run list
        (mirrors the Java behavior).
        """
        import requests

        name = _process_to_name(process)
        if name in self.processes_to_run:
            self.processes_to_run.remove(name)

        payload = {"process_types": [name]}
        r = requests.post(
            f"{self.coms_address}/stop/process", json=payload, timeout=timeout_s
        )
        return r.status_code == 200
'''
