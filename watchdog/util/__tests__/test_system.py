import os
from watchdog.util.system import get_local_hostname, load_basic_system_config


def test_get_local_hostname():
    # Will not work on other computers other than mine
    assert get_local_hostname() == "Deniss-MacBook-Pro.local"


def add_cur_dir(path: str):
    return os.path.join(os.path.dirname(__file__), path)


def test_global_config():
    config = load_basic_system_config()
    assert config is not None
