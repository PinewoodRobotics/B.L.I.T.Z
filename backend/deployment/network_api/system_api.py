from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from collections.abc import Iterable
import posixpath
import shlex
import subprocess
import time

from backend.deployment.network_api.utils import FilePath, FolderPath
from backend.deployment.network_api.zeroconf import (
    DiscoveredNetworkSystem,
)
from backend.deployment.processes import Process


SSH_OPTIONS = (
    "-o StrictHostKeyChecking=no "
    "-o UserKnownHostsFile=/dev/null "
    "-o GlobalKnownHostsFile=/dev/null "
    "-o NumberOfPasswordPrompts=1"
)

SSH_RETRY_ATTEMPTS = 3
SSH_RETRY_DELAY_SECONDS = 0.5


@dataclass(slots=True)
class System:
    """
    Unified Raspberry Pi representation with HTTP API and deployment/discovery capabilities.

    Combines:
    - HTTP watchdog API (set_config, start/stop processes)
    - Zeroconf discovery (discover_all)
    - SSH deployment fields (address, password, port)
    """

    general_info: DiscoveredNetworkSystem

    password: str = dataclasses.field(default="ubuntu")
    user: str = dataclasses.field(default="ubuntu")
    ssh_port: int = dataclasses.field(default=22)
    remote_host: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.remote_host = f"{self.user}@{self.general_info.hostname}"

    def watchdog_url(self) -> str:
        return f"http://{self.general_info.hostname}:{self.general_info.watchdog_port}/"

    def set_config(self, raw_config_base64: str, *, timeout_s: float = 5.0) -> bool:
        """
        Sends configuration to the Pi.

        Note: existing Python tooling uses {"config": "..."} while the Java code
        uses {"config_base64": "..."}. We send BOTH keys for compatibility.
        """
        import requests  # pyright: ignore[reportMissingModuleSource]

        payload = {"config": raw_config_base64, "config_base64": raw_config_base64}
        r = requests.post(
            f"{self.watchdog_url()}/set/config", json=payload, timeout=timeout_s
        )
        return r.status_code == 200

    def set_processes(
        self,
        process_types: Iterable[Process] | None = None,
        *,
        timeout_s: float = 5.0,
    ) -> bool:
        """
        Set the process list on the Pi via POST /set/processes.
        If process_types is provided, also updates self.processes_to_run.
        """
        import requests  # pyright: ignore[reportMissingModuleSource]

        names = [p.get_name() for p in process_types or []]
        payload = {"process_types": names}
        r = requests.post(
            f"{self.watchdog_url()}/set/processes", json=payload, timeout=timeout_s
        )
        if r.status_code != 200:
            print(r.text)
            return False

        return True

    def stop_all_set_config_and_start(
        self,
        raw_config_base64: str,
        *,
        new_processes_to_run: Iterable[Process] | None = None,
        timeout_s: float = 5.0,
    ) -> bool:
        if not self.set_config(raw_config_base64, timeout_s=timeout_s):
            return False

        return self.set_processes(new_processes_to_run, timeout_s=timeout_s)

    def to_blitz_relative_path(self, path: FilePath) -> FilePath:
        return FilePath(posixpath.join(self.general_info.blitz_path, path))

    def _clean_path(self, path: FilePath) -> tuple[FilePath, FolderPath]:
        if path.startswith("/"):
            return path, FolderPath(posixpath.dirname(path))

        return self.to_blitz_relative_path(path), FolderPath(posixpath.dirname(path))

    def deploy_file(
        self, local_file_path: FilePath, remote_file_path: FilePath
    ) -> bool:
        remote_file, remote_dir = self._clean_path(remote_file_path)

        if not self.run_command(f"mkdir -p {shlex.quote(remote_dir)}"):
            return False

        rsync_proc = self._run_with_retries(
            [
                *self._sshpass_command_prefix(),
                "rsync",
                "-av",
                "--progress",
                "-e",
                f"ssh -p {self.ssh_port} {SSH_OPTIONS}",
                str(local_file_path),
                f"{self.remote_host}:{shlex.quote(remote_file)}",
            ],
            "rsync bundle",
        )
        return rsync_proc.returncode == 0

    def run_command(self, command: str) -> bool:
        ssh_proc = self._run_with_retries(
            [
                *self._sshpass_command_prefix(),
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-o",
                "GlobalKnownHostsFile=/dev/null",
                "-o",
                "NumberOfPasswordPrompts=1",
                "-p",
                str(self.ssh_port),
                self.remote_host,
                command,
            ],
            f"ssh {command}",
        )
        return ssh_proc.returncode == 0

    def _sshpass_command_prefix(self) -> list[str]:
        return ["sshpass", "-p", self.password]

    def _run_with_retries(
        self,
        command: list[str],
        label: str,
        *,
        attempts: int = SSH_RETRY_ATTEMPTS,
    ) -> subprocess.CompletedProcess[str]:
        last_proc: subprocess.CompletedProcess[str] | None = None
        for attempt in range(1, attempts + 1):
            proc = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            last_proc = proc
            print(proc.stdout)
            if proc.returncode == 0:
                return proc

            if attempt < attempts:
                print(
                    f"{label} failed on attempt {attempt}/{attempts}; retrying..."
                )
                time.sleep(SSH_RETRY_DELAY_SECONDS)

        assert last_proc is not None
        return last_proc

    def __hash__(self) -> int:
        return hash(self.general_info.hostname)
