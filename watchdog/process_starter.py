from logging import debug, error
import platform
import subprocess
import shlex
import importlib
from typing import Callable

from backend.deployment.util import _RunnableModule
from watchdog.constants import BASIC_SYSTEM_CONFIG_PATH, SYSTEM_NAME_PATH


def get_all_modules() -> list[_RunnableModule]:
    backend_deploy = importlib.import_module("backend.deploy")
    backend_deploy = importlib.reload(backend_deploy)
    modules = backend_deploy.get_modules()
    modules = [m for m in modules if isinstance(m, _RunnableModule)]
    return modules


def _find_module_by_name(name: str):
    modules = get_all_modules()

    for m in modules:
        if m.equivalent_run_definition == name:
            return m

    return None


def get_possible_processes() -> list[str]:
    modules = get_all_modules()
    return [m.equivalent_run_definition for m in modules]


def start_process(process_name: str, config_path: str):
    module = _find_module_by_name(process_name)
    if module is None:
        error(f"Unknown process {process_name}")
        return None

    name_file_path = SYSTEM_NAME_PATH
    basic_system_config_file_path = BASIC_SYSTEM_CONFIG_PATH
    base_cmd = module.get_run_command().strip()
    cmd = f"{base_cmd} --config-file-path {config_path} --name-file-path {name_file_path} --basic-system-config-file-path {basic_system_config_file_path}".strip()
    debug(f"Starting: {cmd}\n")

    return subprocess.Popen(
        shlex.split(cmd),
        text=True,
        bufsize=1,
        universal_newlines=True,
        stderr=subprocess.PIPE,
    )
