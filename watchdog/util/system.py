import argparse
import json
import os
import platform
import re
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import netifaces
import psutil
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


from watchdog.constants import BASIC_SYSTEM_CONFIG_PATH, SYSTEM_NAME_PATH


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

    api_host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("api_host", "host"))
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


class WatchdogSystemConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    autobahn_connection: AutobahnConnectionConfig = Field(
        validation_alias=AliasChoices(
            "autobahn_connection",
            "autobahn",
            "communication",
        )
    )
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
class RuntimePlatformInfo:
    machine_architecture: str
    platform_description: str
    python_major_version: int
    python_minor_version: int
    os_distribution_id: str | None = None
    os_distribution_family: str | None = None
    os_distribution_version_id: str | None = None

    @classmethod
    def collect(cls) -> "RuntimePlatformInfo":
        os_release = read_os_release()

        return cls(
            machine_architecture=platform.machine(),
            platform_description=platform.platform(),
            python_major_version=sys.version_info.major,
            python_minor_version=sys.version_info.minor,
            os_distribution_id=os_release.get("ID"),
            os_distribution_family=os_release.get("ID_LIKE"),
            os_distribution_version_id=os_release.get("VERSION_ID"),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimePlatformInfo":
        return cls(
            machine_architecture=str(
                _required_value_from_mapping(
                    data,
                    "machine_architecture",
                    "platform_machine",
                )
            ),
            platform_description=str(
                _required_value_from_mapping(
                    data,
                    "platform_description",
                    "platform_platform",
                )
            ),
            python_major_version=int(
                _required_value_from_mapping(
                    data,
                    "python_major_version",
                    "python_version_major",
                )
            ),
            python_minor_version=int(
                _required_value_from_mapping(
                    data,
                    "python_minor_version",
                    "python_version_minor",
                )
            ),
            os_distribution_id=_optional_str_from_mapping(
                data,
                "os_distribution_id",
                "os_release_id",
            ),
            os_distribution_family=_optional_str_from_mapping(
                data,
                "os_distribution_family",
                "os_release_id_like",
            ),
            os_distribution_version_id=_optional_str_from_mapping(
                data,
                "os_distribution_version_id",
                "os_release_version_id",
            ),
        )

    @classmethod
    def from_json(cls, raw: str) -> "RuntimePlatformInfo":
        return cls.from_dict(json.loads(raw))

    @classmethod
    def load(cls, path: str | Path) -> "RuntimePlatformInfo":
        return cls.from_json(Path(path).read_text())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def _optional_str_from_mapping(
    data: dict[str, Any], preferred_key: str, legacy_key: str
) -> str | None:
    value = data.get(preferred_key, data.get(legacy_key))
    return None if value is None else str(value)


def _required_value_from_mapping(
    data: dict[str, Any], preferred_key: str, legacy_key: str
) -> Any:
    value = data.get(preferred_key, data.get(legacy_key))
    if value is None:
        raise KeyError(f"Missing required key {preferred_key!r} (or legacy {legacy_key!r})")
    return value
