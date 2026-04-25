from logging import debug, error
import platform
import subprocess
import shlex
import importlib
from typing import Any, Callable

import psutil

from watchdog.constants import BASIC_SYSTEM_CONFIG_PATH, SYSTEM_NAME_PATH


def _is_runnable_module(module: Any) -> bool:
    return hasattr(module, "equivalent_run_definition") and callable(
        getattr(module, "get_run_command", None)
    )


class OpenedProcess(subprocess.Popen[str]):
    def is_alive(self) -> bool:
        try:
            return self.poll() is None
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def stop(self) -> None:
        try:
            parent = psutil.Process(self.pid)
            children = parent.children(recursive=True)
            for child in children:
                debug(f"Killing child process {child.pid}")
                child.terminate()
            gone, alive = psutil.wait_procs(children, timeout=2)
            for child in alive:
                debug(f"Force killing stubborn child process {child.pid}")
                child.kill()
            self.terminate()
            try:
                self.wait(timeout=2)
            except Exception:
                self.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            debug(f"Process already dead or inaccessible")
        try:
            self.kill()
        except Exception:
            pass


class RunnableModules:
    def __init__(self):
        self.runnable_modules: dict[str, Any] = {}

    def reload(self) -> dict[str, Any]:
        modules: list[Any] = []
        try:
            backend_deploy = importlib.import_module("backend.deploy")
            backend_deploy = importlib.reload(backend_deploy)
            modules = backend_deploy.get_modules()
        except Exception as e:
            error(f"Failed to get all modules: {e}")
            modules = []

        self.runnable_modules = {}
        for module in modules:
            if _is_runnable_module(module):
                self.runnable_modules[module.equivalent_run_definition] = module

        return self.runnable_modules

    def get_runnable(self) -> list[Any]:
        self.reload()
        return list(self.runnable_modules.values())

    def get_possible_processes(self) -> list[str]:
        self.reload()
        return list(self.runnable_modules.keys())

    def start_process(
        self, process_name: str, config_path: str
    ) -> OpenedProcess | None:
        self.reload()

        module = self.runnable_modules.get(process_name)
        if module is None:
            error(f"Unknown process {process_name}")
            return None

        name_file_path = SYSTEM_NAME_PATH
        basic_system_config_file_path = BASIC_SYSTEM_CONFIG_PATH
        base_cmd = module.get_run_command().strip()
        cmd = f"{base_cmd} --config-file-path {config_path} --name-file-path {name_file_path} --basic-system-config-file-path {basic_system_config_file_path}".strip()
        debug(f"Starting: {cmd}\n")

        return OpenedProcess(
            shlex.split(cmd),
            text=True,
            bufsize=1,
            universal_newlines=True,
            stderr=subprocess.PIPE,
        )
