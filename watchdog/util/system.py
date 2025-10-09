import argparse
import psutil
import json
import re
from pydantic import BaseModel
import netifaces
import socket


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


class BasicSystemConfig(BaseModel):
    autobahn: AutobahnBaseConfig
    logging: GlobalLoggingBaseConfig
    watchdog: WatchdogBaseConfig
    config_path: str


def get_system_name() -> str:
    with open("system_data/name.txt", "r") as f:
        return f.read().strip()


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

    with open("system_data/basic_system_config.json", "r") as f:
        config_content = f.read()

    config_content = re.sub(r"<system_name>", system_name, config_content)

    config_dict = json.loads(config_content)
    return BasicSystemConfig(**config_dict)


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
