from logging import debug, error
import subprocess
import shlex
import importlib

from backend.deployment.util import RunnableModule


def get_all_modules() -> list[RunnableModule]:
    backend_deploy = importlib.import_module("backend.deploy")
    backend_deploy = importlib.reload(backend_deploy)
    modules = backend_deploy.get_modules()
    if isinstance(modules, RunnableModule):
        modules = [modules]

    return modules


def _find_module_by_name(name: str):
    modules = get_all_modules()

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
