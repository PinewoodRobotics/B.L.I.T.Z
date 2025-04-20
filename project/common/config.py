import subprocess
import json

from generated.thrift.config.ttypes import Config


def load_config(config_path: str = "config/") -> Config:
    try:
        result = subprocess.run(
            ["npx", "tsx", config_path], capture_output=True, text=True, check=True
        )
        config_json = result.stdout
        config_dict = json.loads(config_json)
        return Config(**config_dict)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to run 'tsc config/': {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON output from tsc: {e}")


def from_file(file_path: str) -> Config:
    with open(file_path, "r") as f:
        config_json = f.read()
    config_dict = json.loads(config_json)
    return Config(**config_dict)


def from_uncertainty_config(file_path: str | None = None) -> Config:
    if file_path is None:
        return load_config()

    return from_file(file_path)


def from_json(json_str: str) -> Config:
    config_dict = json.loads(json_str)
    return Config(**config_dict)
