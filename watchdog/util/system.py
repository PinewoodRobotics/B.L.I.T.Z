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
import sysconfig
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


def safe_run(cmd):
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return {
            "returncode": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
        }
    except Exception as e:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }


def guess_implementation_short():
    name = platform.python_implementation()
    mapping = {
        "CPython": "cp",
        "PyPy": "pp",
        "Jython": "jy",
        "IronPython": "ip",
    }
    return mapping.get(name, name.lower())


def guess_abi():
    """
    Best-effort ABI guess.
    For CPython this is usually cpXY, e.g. cp311.
    """
    impl = guess_implementation_short()
    ver = f"{sys.version_info.major}{sys.version_info.minor}"
    if impl == "cp":
        return f"cp{ver}"
    return None


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
    def collect(cls) -> "RaspberryPiInfo":
        pip_ver = safe_run([sys.executable, "-m", "pip", "--version"])
        pip_version = (
            pip_ver["stdout"].strip() if isinstance(pip_ver["stdout"], str) else ""
        ) or (pip_ver["stderr"].strip() if isinstance(pip_ver["stderr"], str) else "")
        os_release = read_os_release()

        return cls(
            os_name=os.name,
            sys_platform=sys.platform,
            platform_system=platform.system(),
            platform_release=platform.release(),
            platform_version=platform.version(),
            platform_machine=platform.machine(),
            platform_platform=platform.platform(),
            python_executable=sys.executable,
            python_version=platform.python_version(),
            python_version_major=sys.version_info.major,
            python_version_minor=sys.version_info.minor,
            python_version_micro=sys.version_info.micro,
            python_implementation=platform.python_implementation(),
            implementation_short=guess_implementation_short(),
            abi_guess=guess_abi(),
            sys_abiflags=getattr(sys, "abiflags", ""),
            soabi=sysconfig.get_config_var("SOABI"),
            ext_suffix=sysconfig.get_config_var("EXT_SUFFIX"),
            pip_version=pip_version,
            os_release_pretty_name=os_release.get("PRETTY_NAME"),
            os_release_name=os_release.get("NAME"),
            os_release_id=os_release.get("ID"),
            os_release_id_like=os_release.get("ID_LIKE"),
            os_release_version=os_release.get("VERSION"),
            os_release_version_id=os_release.get("VERSION_ID"),
            os_release_version_codename=os_release.get("VERSION_CODENAME"),
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
