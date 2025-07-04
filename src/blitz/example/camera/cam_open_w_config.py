import json
import time
import requests
from blitz.common.config import get_config_raw
from blitz.common.util.system import ProcessType, load_basic_system_config

config_raw = get_config_raw()
config_dict = json.loads(config_raw)
config_base64 = config_dict["binary_base64"]
basic_system_config = load_basic_system_config()

response = requests.post(
    f"http://10.47.65.7:{basic_system_config.watchdog.port}/set/config",
    json={"config": config_base64},
)

print(f"Camera Setting Config Output: {response.json()}")

response = requests.post(
    f"http://10.47.65.7:{basic_system_config.watchdog.port}/start/process",
    json={"process_types": [ProcessType.CAMERA_PROCESSING.value]},
)

print(f"Camera Starting Process Output: {response.json()}")

print(f"Stopping in 50 seconds")
time.sleep(50)

response = requests.post(
    f"http://10.47.65.7:{basic_system_config.watchdog.port}/stop/process",
    json={"process_types": [ProcessType.CAMERA_PROCESSING.value]},
)

print(f"Camera Stopping Process Output: {response.json()}")
