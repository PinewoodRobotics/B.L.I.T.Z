import os
from pathlib import Path


def get_basic_system_config_path() -> str:
    return "system_data/basic_system_config.json"


def get_system_name_path() -> str:
    return "system_data/name.txt"


def get_blitz_path() -> str:
    return os.environ.get("BLITZ_PATH") or str(Path(__file__).resolve().parents[1])


BASIC_SYSTEM_CONFIG_PATH = get_basic_system_config_path()
SYSTEM_NAME_PATH = get_system_name_path()
BLITZ_PATH = get_blitz_path()
BUNDLE_FOLDER_PATH = os.path.join(BLITZ_PATH, "backend")
