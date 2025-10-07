import json
import time
import requests
from backend.python.common.config import get_config_raw
from backend.python.common.util.system import ProcessType, load_basic_system_config

config_base64 = get_config_raw()
basic_system_config = load_basic_system_config()
host = "raspberrypi1.local"

response = requests.post(
    f"http://{host}:{basic_system_config.watchdog.port}/set/config",
    json={"config": config_base64},
)

print(f"Lidar 3D Setting Config Output: {response.json()}")

stop_response = requests.post(
    f"http://{host}:{basic_system_config.watchdog.port}/stop/process",
    json={"process_types": ["pos_extrapolator"]},
)

print(f"Lidar 3D Stopping Process Output: {stop_response.json()}")

response = requests.post(
    f"http://{host}:{basic_system_config.watchdog.port}/start/process",
    json={
        "process_types": [
            "pos_extrapolator",
        ]
    },
)

print(f"Pos Extrapolator Starting Process Output: {response.json()}")
