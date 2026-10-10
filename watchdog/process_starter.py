import subprocess
import shlex
import os

import psutil

from watchdog.ext.expected_deployment_struct import RunnableModule
from watchdog.util.logger import debug


class OpenedProcess(subprocess.Popen[str]):
    def is_alive(self) -> bool:
        try:
            return self.poll() is None and self.returncode is None
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def stop(self) -> None:
        try:
            parent = psutil.Process(self.pid)
            children = parent.children(recursive=True)
            for child in children:
                debug(f"Killing child process {child.pid}")
                child.terminate()
            _, alive = psutil.wait_procs(children, timeout=2)
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

    @staticmethod
    def _format_flags(flags: dict[str, str]) -> str:
        return " ".join([f"--{flag} {value}" for flag, value in flags.items()])

    @classmethod
    def start_module(
        cls, module: RunnableModule, bundle_path: str, flags: dict[str, str]
    ) -> "OpenedProcess":
        bundle_path = os.path.abspath(bundle_path)
        flags = dict(flags)
        for key in ("config-path", "basic-system-config-path", "blitz-path", "bundle-folder-path"):
            if key in flags:
                flags[key] = os.path.abspath(flags[key])
        argv = module.get_run_argv(bundle_path, flags.get("blitz-path"))
        if module.launch.accepts_blitz_flags:
            argv.extend(part for key, value in flags.items() for part in (f"--{key}", value))
        debug(f"Starting: {shlex.join(argv)}\n")
        environment = os.environ.copy()
        environment.update(module.get_run_environment(bundle_path))
        environment.update({"BLITZ_" + key.upper().replace("-", "_"): value for key, value in flags.items()})

        return cls(
            argv,
            cwd=module.get_run_directory(bundle_path),
            env=environment,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
