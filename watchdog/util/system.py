import argparse
import os
import subprocess
import psutil
import json
import re
from pydantic import BaseModel
import netifaces
import socket
from dataclasses import asdict, dataclass
import platform
import sys
from pathlib import Path
from typing import Any


from watchdog.constants import BASIC_SYSTEM_CONFIG_PATH, SYSTEM_NAME_PATH


class AutobahnBaseConfig(BaseModel):
    host: str
    port: int


class GlobalLoggingBaseConfig(BaseModel):
    global_log_pub_topic: str
    global_logging_publishing_enabled: bool
    global_logging_level: str


class WatchdogBaseConfig(BaseModel):
    host: str
    port: int
    stats_pub_period_s: float
    send_stats: bool
    process_memory_file: str


class BasicSystemConfig(BaseModel):
    autobahn: AutobahnBaseConfig
    logging: GlobalLoggingBaseConfig
    watchdog: WatchdogBaseConfig
    config_path: str


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


def load_basic_system_config() -> BasicSystemConfig:
    system_name = get_system_name()

    with open(BASIC_SYSTEM_CONFIG_PATH, "r") as f:
        config_content = f.read()

    config_content = re.sub(r"<system_name>", system_name, config_content)

    return BasicSystemConfig(**json.loads(config_content))


def get_system_name() -> str:
    with open(SYSTEM_NAME_PATH, "r") as f:
        return f.read().strip()


def get_primary_ipv4():
    """
    Returns the IPv4 address used for the system's default route.
    This is the true outbound interface (Ethernet if WiFi is off).
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

    except Exception as e:
        raise RuntimeError(f"Failed to determine primary IPv4 address: {e}")


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


@dataclass
class RaspberryPiInfo:
    platform_machine: str
    platform_platform: str
    python_version_major: int
    python_version_minor: int
    os_release_id: str | None = None
    os_release_id_like: str | None = None
    os_release_version_id: str | None = None

    @classmethod
    def collect(cls) -> "RaspberryPiInfo":
        os_release = read_os_release()

        return cls(
            platform_machine=platform.machine(),
            platform_platform=platform.platform(),
            python_version_major=sys.version_info.major,
            python_version_minor=sys.version_info.minor,
            os_release_id=os_release.get("ID"),
            os_release_id_like=os_release.get("ID_LIKE"),
            os_release_version_id=os_release.get("VERSION_ID"),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RaspberryPiInfo":
        return cls(**data)

    @classmethod
    def from_json(cls, raw: str) -> "RaspberryPiInfo":
        return cls.from_dict(json.loads(raw))

    @classmethod
    def load(cls, path: str | Path) -> "RaspberryPiInfo":
        return cls.from_json(Path(path).read_text())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)
