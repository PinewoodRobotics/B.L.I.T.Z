from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from collections.abc import Iterable
import os
import posixpath
import shlex
import subprocess
from typing import override

from backend.deployment.misc import output
from backend.deployment.network_api.zeroconf import (
    DiscoveredNetworkSystem,
)
from backend.deployment.processes import Process


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

    last_deploy_file_diagnostics: dict[str, object] = field(
        default_factory=dict,
        init=False,
    )
    last_run_command_diagnostics: dict[str, object] = field(
        default_factory=dict,
        init=False,
    )

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

    def deploy_file(self, file_path: str, remote_file_path: str) -> bool:
        remote_host = f"{self.user}@{self.general_info.hostname}"
        remote_destination = (
            remote_file_path
            if remote_file_path.startswith("/")
            else posixpath.join(self.general_info.blitz_path, remote_file_path)
        )
        remote_target_dir = posixpath.dirname(remote_destination)

        rsync_cmd = [
            "sshpass",
            "-p",
            self.password,
            "rsync",
            "-av",
            "--progress",
            f"--rsync-path=mkdir -p {shlex.quote(remote_target_dir)} && rsync",
            "-e",
            f"ssh -p {self.ssh_port} -o StrictHostKeyChecking=no",
            file_path,
            f"{remote_host}:{shlex.quote(remote_destination)}",
        ]
        redacted_rsync_cmd = [*rsync_cmd]
        redacted_rsync_cmd[2] = "<redacted>"
        self.last_deploy_file_diagnostics = {
            "local_file": file_path,
            "local_file_exists": os.path.exists(file_path),
            "local_file_size": (
                os.path.getsize(file_path) if os.path.exists(file_path) else None
            ),
            "remote_host": remote_host,
            "remote_destination": remote_destination,
            "remote_target_dir": remote_target_dir,
            "ssh_port": self.ssh_port,
            "ssh_user": self.user,
            "watchdog_url": self.watchdog_url(),
            "command": shlex.join(redacted_rsync_cmd),
        }

        try:
            rsync_proc = subprocess.run(
                rsync_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as error:
            self.last_deploy_file_diagnostics.update(
                {
                    "exception_type": type(error).__name__,
                    "exception": str(error),
                }
            )
            output.command_failure(
                f"rsync {self.general_info.hostname}",
                [f"{type(error).__name__}: {error}"],
            )
            return False

        stdout_lines = rsync_proc.stdout.splitlines() if rsync_proc.stdout else []
        self.last_deploy_file_diagnostics.update(
            {
                "returncode": rsync_proc.returncode,
                "output_line_count": len(stdout_lines),
                "output_tail": stdout_lines[-25:],
            }
        )
        if rsync_proc.stdout:
            output.command_output(rsync_proc.stdout)
        if rsync_proc.returncode != 0:
            output.command_failure(
                f"rsync {self.general_info.hostname}",
                rsync_proc.stdout.splitlines()[-25:] if rsync_proc.stdout else [],
            )
        return rsync_proc.returncode == 0

    def run_command(self, command: str) -> bool:
        ssh_cmd = [
            "sshpass",
            "-p",
            self.password,
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-p",
            str(self.ssh_port),
            f"{self.user}@{self.general_info.hostname}",
            command,
        ]
        redacted_ssh_cmd = [*ssh_cmd]
        redacted_ssh_cmd[2] = "<redacted>"
        self.last_run_command_diagnostics = {
            "transport": "ssh",
            "remote_host": f"{self.user}@{self.general_info.hostname}",
            "ssh_port": self.ssh_port,
            "watchdog_url": self.watchdog_url(),
            "command": command,
            "exec_command": shlex.join(redacted_ssh_cmd),
        }

        ssh_proc = subprocess.run(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stdout_lines = ssh_proc.stdout.splitlines() if ssh_proc.stdout else []
        self.last_run_command_diagnostics.update(
            {
                "returncode": ssh_proc.returncode,
                "output_line_count": len(stdout_lines),
                "output_tail": stdout_lines[-25:],
            }
        )
        if ssh_proc.stdout:
            output.command_output(ssh_proc.stdout)
        if ssh_proc.returncode != 0:
            output.command_failure(
                f"ssh {self.general_info.hostname}",
                ssh_proc.stdout.splitlines()[-25:] if ssh_proc.stdout else [],
            )
        return ssh_proc.returncode == 0

    @override
    def __hash__(self) -> int:
        return hash(self.general_info.hostname)
