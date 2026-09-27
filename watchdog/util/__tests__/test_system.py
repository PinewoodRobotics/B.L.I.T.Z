import os
import subprocess
from watchdog.util.system import get_local_hostname, load_basic_system_config


def test_get_local_hostname():
    machine_hostname = subprocess.check_output(["hostname"], text=True).strip()
    expected_hostname = (
        machine_hostname
        if machine_hostname.endswith(".local")
        else f"{machine_hostname}.local"
    )

    assert get_local_hostname(include_local_suffix=False) == machine_hostname
    assert get_local_hostname() == expected_hostname


def add_cur_dir(path: str):
    return os.path.join(os.path.dirname(__file__), path)


def test_global_config():
    config = load_basic_system_config()
    assert config is not None
