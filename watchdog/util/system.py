import argparse
import json
import ipaddress
import os
import platform
import re
import socket
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import netifaces
import psutil
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


from watchdog.constants import BASIC_SYSTEM_CONFIG_PATH, SYSTEM_NAME_PATH
from watchdog.util.capabilities import collect_capabilities


class AutobahnConnectionConfig(BaseModel):
    host: str
    port: int


class WatchdogLoggingConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    log_publish_topic: str = Field(
        validation_alias=AliasChoices(
            "log_publish_topic",
            "log_pub_topic",
            "global_log_pub_topic",
        )
    )
    publish_logs_over_autobahn: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "publish_logs_over_autobahn",
            "global_logging_publishing_enabled",
        ),
    )
    default_log_level: str = Field(
        validation_alias=AliasChoices(
            "default_log_level",
            "logging_level",
            "global_logging_level",
        )
    )


class WatchdogApiConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    api_host: str = Field(
        default="0.0.0.0", validation_alias=AliasChoices("api_host", "host")
    )
    api_port: int = Field(validation_alias=AliasChoices("api_port", "port"))
    system_stats_publish_interval_seconds: float = Field(
        validation_alias=AliasChoices(
            "system_stats_publish_interval_seconds",
            "stats_pub_period_s",
        )
    )
    publish_system_stats: bool = Field(
        validation_alias=AliasChoices(
            "publish_system_stats",
            "send_system_stats",
            "send_stats",
        )
    )
    managed_process_state_file: str = Field(
        default="config/processes.json",
        validation_alias=AliasChoices(
            "managed_process_state_file",
            "process_memory_file",
        ),
    )


class WatchdogDiscoveryConfig(BaseModel):
    """Reachable endpoints may differ from container-local listening ports."""

    hostname: str | None = None
    addresses: list[str] = Field(default_factory=list)
    watchdog_host: str | None = None
    watchdog_port: int | None = Field(default=None, ge=1, le=65535)
    autobahn_host: str | None = None
    autobahn_port: int | None = Field(default=None, ge=1, le=65535)
    ssh_host: str | None = None
    ssh_port: int = Field(default=22, ge=1, le=65535)
    catalog_refresh_interval_seconds: float = Field(default=300.0, gt=0)


class WatchdogSystemConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    autobahn_connection: AutobahnConnectionConfig = Field(
        validation_alias=AliasChoices(
            "autobahn_connection",
            "autobahn",
            "communication",
        )
    )
    discovery: WatchdogDiscoveryConfig = Field(default_factory=WatchdogDiscoveryConfig)
    logging: WatchdogLoggingConfig
    watchdog_api: WatchdogApiConfig = Field(
        validation_alias=AliasChoices("watchdog_api", "watchdog")
    )
    desired_config_base64_path: str = Field(
        validation_alias=AliasChoices(
            "desired_config_base64_path",
            "intended_config_path",
            "config_path",
        )
    )


BasicSystemConfig = WatchdogSystemConfig


def get_top_10_processes() -> list[psutil.Process]:
    processes = sorted(
        [
            p
            for p in psutil.process_iter(attrs=["pid", "name", "cpu_percent"])
            if p.info["cpu_percent"] is not None
        ],
        key=lambda p: p.info["cpu_percent"],
        reverse=True,
    )

    return processes[:10]


def load_basic_system_config() -> WatchdogSystemConfig:
    system_name = get_system_name()

    with open(BASIC_SYSTEM_CONFIG_PATH, "r") as f:
        config_content = f.read()

    config_content = re.sub(r"<system_name>", system_name, config_content)

    return WatchdogSystemConfig(**json.loads(config_content))


def get_system_name() -> str:
    with open(SYSTEM_NAME_PATH, "r") as f:
        return f.read().strip()


def get_primary_ipv4() -> str:
    """
    Prefer the default-route source, then an active LAN address on offline systems.
    Querying the route table does not send traffic to the internet.
    """
    try:
        result = subprocess.run(
            ["ip", "route", "get", "1.1.1.1"],
            capture_output=True,
            text=True,
            check=True,
        )

        parts = result.stdout.split()

        src_index = parts.index("src") + 1
        ip = parts[src_index]

        socket.inet_aton(ip)
        return ip

    except (OSError, subprocess.CalledProcessError, ValueError, IndexError) as error:
        route_error = error

    # A directly connected offline LAN may have no default gateway. Prefer
    # physical Ethernet/WiFi interfaces over auxiliary bridges, then link-local
    # addresses only when no other active IPv4 address is available.
    stats = psutil.net_if_stats()
    link_local: list[str] = []
    interfaces = sorted(netifaces.interfaces(), key=lambda name: (not name.startswith(("eth", "en", "wl")), name))
    for interface in interfaces:
        if interface not in stats or not stats[interface].isup:
            continue
        for record in netifaces.ifaddresses(interface).get(netifaces.AF_INET, []):
            try:
                address = ipaddress.IPv4Address(record.get("addr", ""))
            except ValueError:
                continue
            if address.is_loopback or address.is_unspecified or address.is_multicast:
                continue
            if address.is_link_local:
                link_local.append(str(address))
            else:
                return str(address)
    if link_local:
        return link_local[0]
    raise RuntimeError(f"Failed to determine primary IPv4 address: no active LAN address (route query: {route_error})")


def get_local_ip(iface: str = "eth0") -> str | None:
    """
    Returns the IPv4 address for the given interface (e.g. "eth0" or "en0"),
    or None if the interface isn't found or has no IPv4 address.
    """
    try:
        addrs = netifaces.ifaddresses(iface)
        ipv4 = addrs.get(netifaces.AF_INET, [])
        if ipv4 and "addr" in ipv4[0]:
            return ipv4[0]["addr"]
    except ValueError:
        pass
    return None


def get_local_hostname(include_local_suffix: bool = True) -> str:
    hostname = socket.gethostname()
    if include_local_suffix and not hostname.endswith(".local"):
        return f"{hostname}.local"
    return hostname


def get_config_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--config", type=str, default=None)
    return parser


def get_camera_video_ports() -> list[str]:
    ports = []
    symlink_names = ["usb_cam1", "usb_cam2", "usb_cam3", "usb_cam4"]
    for name in symlink_names:
        path = f"/dev/{name}"
        if os.path.exists(path):
            ports.append(path)
    return ports


def get_camera_tty_ports() -> list[str]:
    ports = []
    symlink_names = ["usb_cam1_tty", "usb_cam2_tty", "usb_cam3_tty", "usb_cam4_tty"]
    for name in symlink_names:
        path = f"/dev/{name}"
        if os.path.exists(path):
            ports.append(path)
    return ports


def read_os_release() -> dict[str, str]:
    os_release_path = Path("/etc/os-release")
    if not os_release_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in os_release_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key] = value.strip().strip("\"'")
    return values


CATALOG_SCHEMA_VERSION = 2


@dataclass
class DiscoveryAnnouncement:
    """Cheap connection metadata; never probes hardware or system profiles."""

    hostname: str
    system_name: str
    watchdog_port: int
    autobahn_port: int
    ssh_port: int
    watchdog_host: str
    autobahn_host: str
    ssh_host: str
    schema_version: int = CATALOG_SCHEMA_VERSION

    @classmethod
    def collect(cls, config: WatchdogSystemConfig | None = None) -> "DiscoveryAnnouncement":
        config = config or load_basic_system_config()
        discovery = config.discovery
        hostname = discovery.hostname or get_local_hostname()

        def reachable_host(value: str | None) -> str:
            if not value or value.rstrip(".").lower() == "localhost":
                return hostname
            try:
                address = ipaddress.ip_address(value)
                if address.is_loopback or address.is_unspecified:
                    return hostname
            except ValueError:
                pass
            return value
        return cls(
            hostname=hostname,
            system_name=get_system_name(),
            watchdog_port=discovery.watchdog_port or config.watchdog_api.api_port,
            autobahn_port=discovery.autobahn_port or config.autobahn_connection.port,
            ssh_port=discovery.ssh_port,
            # Explicit discovery hosts describe the client's network view,
            # including loopback for clients running on the Docker host.
            watchdog_host=discovery.watchdog_host or hostname,
            autobahn_host=discovery.autobahn_host or reachable_host(config.autobahn_connection.host),
            ssh_host=discovery.ssh_host or hostname,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiscoveredNetworkSystem:
    hostname: str
    system_name: str
    watchdog_port: int
    autobahn_port: int
    blitz_path: str
    machine_architecture: str
    platform_description: str
    python_major_version: int
    python_minor_version: int
    os_distribution_id: str | None = None
    os_distribution_family: str | None = None
    os_distribution_version_id: str | None = None
    capabilities_json: str = "{}"
    ssh_port: int = 22
    watchdog_host: str | None = None
    autobahn_host: str | None = None
    ssh_host: str | None = None

    @classmethod
    def collect(cls) -> "DiscoveredNetworkSystem":
        os_release = read_os_release()
        system_config = load_basic_system_config()
        announcement = DiscoveryAnnouncement.collect(system_config)
        machine_architecture = platform.machine()
        blitz_path = os.environ.get("BLITZ_PATH") or str(
            Path(__file__).resolve().parents[2]
        )

        return cls(
            capabilities_json=json.dumps(collect_capabilities(os_release, machine_architecture), sort_keys=True),
            hostname=announcement.hostname,
            system_name=announcement.system_name,
            watchdog_port=announcement.watchdog_port,
            autobahn_port=announcement.autobahn_port,
            ssh_port=announcement.ssh_port,
            watchdog_host=announcement.watchdog_host,
            autobahn_host=announcement.autobahn_host,
            ssh_host=announcement.ssh_host,
            blitz_path=blitz_path,
            machine_architecture=machine_architecture,
            platform_description=platform.platform(),
            python_major_version=sys.version_info.major,
            python_minor_version=sys.version_info.minor,
            os_distribution_id=os_release.get("ID"),
            os_distribution_family=os_release.get("ID_LIKE"),
            os_distribution_version_id=os_release.get("VERSION_ID"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SystemCatalogCache:
    """A single atomic hardware snapshot shared by all HTTP callers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._profile: DiscoveredNetworkSystem | None = None
        self._collected_at = 0.0
        self._refresh_interval = 300.0
        self._last_error: Exception | None = None

    def get(self) -> dict[str, Any]:
        with self._lock:
            config = load_basic_system_config()
            self._refresh_interval = config.discovery.catalog_refresh_interval_seconds
            now = time.monotonic()
            if (self._profile is None and self._last_error is None) or now - self._collected_at >= self._refresh_interval:
                self._collected_at = now
                try:
                    profile = DiscoveredNetworkSystem.collect()
                except Exception as error:
                    # Also rate-limit failed probes; repeated HTTP requests must
                    # not hammer a device whose hardware probe is failing.
                    self._last_error = error
                else:
                    self._profile = profile
                    self._last_error = None
                self._collected_at = time.monotonic()
            if self._last_error is not None:
                raise RuntimeError(f"System catalog collection failed: {self._last_error}") from self._last_error
            assert self._profile is not None
            # Reachability and identity remain live while expensive hardware/ABI
            # checks reuse the cached snapshot. A port/name config change should
            # not create a mismatch with the latest lightweight announcement.
            system = self._profile.to_dict()
            announcement = DiscoveryAnnouncement.collect(config).to_dict()
            announcement.pop("schema_version")
            system.update(announcement)
            return {"schema_version": CATALOG_SCHEMA_VERSION, "system": system}


system_catalog_cache = SystemCatalogCache()
