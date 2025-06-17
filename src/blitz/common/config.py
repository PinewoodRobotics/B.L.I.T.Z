import subprocess
import json
from typing import Dict, Any

from blitz.generated.thrift.config.ttypes import Config
from blitz.common.util.thrift_loader import dict_to_thrift


def load_config() -> Config:
    try:
        result = subprocess.run(
            ["npm", "run", "config", "--silent"],
            capture_output=True,
            text=True,
            check=True,
        )
        config_json = result.stdout
        print(config_json)
        config_dict = json.loads(config_json)
        return load_config_from_dict(config_dict)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to run 'npm run config': {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON output from npm run config: {e}")


def from_file(file_path: str) -> Config:
    with open(file_path, "r") as f:
        config_json = f.read()
    return from_json(config_json)


def from_uncertainty_config(file_path: str | None = None) -> Config:
    if file_path is None:
        return load_config()

    return from_file(file_path)


def from_json(json_str: str) -> Config:
    config_dict = json.loads(json_str)
    return load_config_from_dict(config_dict)


def load_config_from_dict(config_dict: Dict[str, Any]) -> Config:
    return dict_to_thrift(Config, config_dict)
