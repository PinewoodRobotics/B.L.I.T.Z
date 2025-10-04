from dataclasses import dataclass
import subprocess
import json
from typing import Dict, Any

from backend.generated.thrift.config.ttypes import Config
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
import base64


@dataclass
class ConfigGetterOutput:
    json: str
    binary_base64: str


def load_config() -> Config:
    try:
        return from_base64(get_config_raw())
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to run 'npm run config': {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON output from npm run config: {e}")


def get_config_raw() -> str:
    try:
        result = subprocess.run(
            ["npm", "run", "config", "--silent"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to run 'npm run config': {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON output from npm run config: {e}")


def from_file(file_path: str) -> Config:
    with open(file_path, "r") as f:
        config_json = f.read()
    return from_base64(config_json)


def from_uncertainty_config(file_path: str | None = None) -> Config:
    if file_path is None:
        return load_config()

    return from_file(file_path)


def from_base64(base64_str: str) -> Config:
    buffer = base64.b64decode(base64_str)
    transport = TTransport.TMemoryBuffer(buffer)
    protocol = TBinaryProtocol.TBinaryProtocol(transport)
    config = Config()
    config.read(protocol)

    return config
