from enum import Enum
import psutil
import json
import re
from pydantic import BaseModel


class ProcessType(Enum):
    POS_EXTRAPOLATOR = "position-extrapolator"
    LIDAR_READER_2D = "lidar-reader-2d"
    LIDAR_POINT_PROCESSOR = "lidar-point-processor"
    LIDAR_PROCESSING = "lidar-processing"
    CAMERA_PROCESSING = "april-server"
    ABC = "abc"


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
