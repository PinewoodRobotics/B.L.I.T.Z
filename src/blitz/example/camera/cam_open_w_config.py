import json
import time
import requests
from blitz.common.config import get_config_raw
from blitz.common.util.system import ProcessType, load_basic_system_config

config_base64 = get_config_raw()
basic_system_config = load_basic_system_config()

response = requests.post(
    f"http://10.47.65.7:{basic_system_config.watchdog.port}/set/config",
    json={"config": config_base64},
)

print(f"Lidar 3D Setting Config Output: {response.json()}")

stop_response = requests.post(
    f"http://10.47.65.7:{basic_system_config.watchdog.port}/stop/process",
    json={
        "process_types": [
            ProcessType.POS_EXTRAPOLATOR.value,
        ]
    },
)

print(f"Lidar 3D Stopping Process Output: {stop_response.json()}")

response = requests.post(
    f"http://10.47.65.7:{basic_system_config.watchdog.port}/start/process",
    json={
        "process_types": [
            ProcessType.POS_EXTRAPOLATOR.value,
        ]
    },
)

print(f"Pos Extrapolator Starting Process Output: {response.json()}")
