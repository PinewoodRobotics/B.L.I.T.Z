from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
import os
from pathlib import Path
import posixpath
import shlex
import subprocess
import tempfile
import time

from backend.deployment.network_api.utils import FilePath, FolderPath
from backend.deployment.network_api.catalog import SystemCatalog
from backend.deployment.network_api.zeroconf import http_authority
from backend.deployment.processes import Process
from backend.deployment.misc.report import remote_output


SSH_OPTIONS = (
    "-o StrictHostKeyChecking=no "
    "-o UserKnownHostsFile=/dev/null "
    "-o GlobalKnownHostsFile=/dev/null "
    "-o NumberOfPasswordPrompts=1"
)

SSH_RETRY_ATTEMPTS = 3
SSH_RETRY_DELAY_SECONDS = 0.5


@contextmanager
def _ssh_password_environment(password: str) -> Iterator[dict[str, str]]:
    """Supply passwords through OpenSSH without relying on sshpass's PTY.

    macOS can intermittently lose sshpass's controlling terminal. Force the
    native helper for both SSH and rsync's SSH child, independent of DISPLAY.
    The helper contains no credentials and rejects non-password prompts.
    """
    with tempfile.TemporaryDirectory(prefix="blitz-ssh-") as directory:
        helper = Path(directory) / "askpass"
        helper.write_text(
            '#!/bin/sh\n'
            'case "$1" in\n'
            '  *assword:*) printf "%s\\n" "$BLITZ_SSH_PASSWORD" ;;\n'
            '  *) exit 1 ;;\n'
            'esac\n'
        )
        helper.chmod(0o700)
        yield {
            **os.environ,
            "SSH_ASKPASS": str(helper),
            "SSH_ASKPASS_REQUIRE": "force",
            "BLITZ_SSH_PASSWORD": password,
        }


@dataclass(slots=True)
class System:
    """
    Unified Raspberry Pi representation with HTTP API and deployment/discovery capabilities.

    Combines:
    - HTTP watchdog API (set_config, start/stop processes)
    - Zeroconf discovery (discover_all)
    - SSH deployment fields (address, password, port)
    """

    general_info: SystemCatalog

    password: str = dataclasses.field(default="ubuntu")
    user: str = dataclasses.field(default="ubuntu")
    ssh_port: int | None = dataclasses.field(default=None)

    def __post_init__(self) -> None:
        self.ssh_port = self.ssh_port or self.general_info.ssh_port

    @property
    def remote_host(self) -> str:
        host = self.general_info.ssh_host or self.general_info.hostname
        return f"{self.user}@{host}"

    def watchdog_url(self) -> str:
        host = self.general_info.watchdog_host or self.general_info.hostname
        return f"http://{http_authority(host, self.general_info.watchdog_port)}/"

    def set_config(self, raw_config_base64: str, *, timeout_s: float = 5.0) -> bool:
        """Send configuration through the watchdog's canonical payload field."""
        import requests  # pyright: ignore[reportMissingModuleSource]

        payload = {"config_base64": raw_config_base64}
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
                "rsync",
                "-av",
                "--progress",
                "-e",
                f"ssh -p {self.ssh_port} {SSH_OPTIONS}",
                str(local_file_path),
                f"{self._rsync_remote_host()}:{shlex.quote(remote_file)}",
            ],
            "rsync bundle",
        )
        return rsync_proc.returncode == 0

    def _rsync_remote_host(self) -> str:
        host = self.general_info.ssh_host or self.general_info.hostname
        return f"{self.user}@[{host}]" if ":" in host else f"{self.user}@{host}"

    def run_command(self, command: str) -> bool:
        ssh_proc = self._run_with_retries(
            [
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
            f"SSH on {self.general_info.hostname}",
        )
        return ssh_proc.returncode == 0

    def _run_with_retries(
        self,
        command: list[str],
        label: str,
        *,
        attempts: int = SSH_RETRY_ATTEMPTS,
    ) -> subprocess.CompletedProcess[str]:
        last_proc: subprocess.CompletedProcess[str] | None = None
        with _ssh_password_environment(self.password) as environment:
            for attempt in range(1, attempts + 1):
                proc = subprocess.run(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=environment,
                )
                last_proc = proc
                if not remote_output(proc.stdout, proc.returncode, attempt):
                    print(proc.stdout)
                if proc.returncode == 0:
                    return proc

                if attempt < attempts:
                    print(
                        f"[WARN] {label}: attempt {attempt}/{attempts} failed; retrying..."
                    )
                    time.sleep(SSH_RETRY_DELAY_SECONDS)

        assert last_proc is not None
        return last_proc

    def __hash__(self) -> int:
        return hash(self.general_info)
