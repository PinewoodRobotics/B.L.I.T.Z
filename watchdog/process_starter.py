from logging import debug, error
import subprocess
import shlex
import importlib
from typing import Callable

from backend.deployment.util import CommonModule


def _find_module_by_name(name: str):
    backend_deploy = importlib.import_module("backend.deploy")
    _ = importlib.reload(backend_deploy)

    get_modules: Callable[[], list[CommonModule] | CommonModule] = getattr(
        backend_deploy, "get_modules"
    )

    modules = get_modules()
    if not isinstance(modules, list):
        modules = [modules]

    for m in modules:
        if m.equivalent_run_definition == name:
            return m

    return None


def start_process(process_name: str, config_path: str):
    module = _find_module_by_name(process_name)
    if module is None:
        error(f"Unknown process {process_name}")
        return None
    base_cmd = module.get_run_command().strip()
    cmd = f"{base_cmd} --config {config_path}".strip()
    debug(f"Starting: {cmd}\n")

    try:
        return subprocess.Popen(
            shlex.split(cmd),
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
    except subprocess.SubprocessError as e:
        error(f"Failed to start {process_name}: {str(e)}")
        return None
