from __future__ import annotations

import tarfile
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from collections.abc import Iterable
import shlex
from uuid import uuid4

import docker
from docker.errors import APIError, DockerException, NotFound
from docker.models.containers import Container
from docker.models.networks import Network
from docker.types import LogConfig

from __tests__.docker_resources import DockerTestResources


@dataclass(frozen=True)
class ExecResult:
    exit_code: int
    output: str


class DockerTestRunner:
    def __init__(self, repo_root: Path, resources: DockerTestResources):
        self.repo_root = repo_root
        self.resources = resources
        self.client = docker.from_env()
        self.containers: list[Container] = []
        self.networks: list[Network] = []

    def build_image(self, dockerfile: str, tag_prefix: str) -> str:
        # Different test cases share one immutable image for each Dockerfile.
        # tag_prefix remains accepted for existing callers; ownership is scoped
        # to the session instead of creating a new timestamp tag for every test.
        return self.resources.installation_image(self.repo_root, dockerfile)

    def create_network(self, name_suffix: str) -> Network:
        network_name = f"{self.resources.name}-{name_suffix}-{uuid4().hex[:8]}"
        try:
            network = self.client.networks.create(network_name, driver="bridge", labels=self.resources.labels)
        except (APIError, DockerException) as error:
            raise AssertionError(f"Failed to create Docker network {network_name}") from error

        self.networks.append(network)
        return network

    def start_container(
        self,
        image_tag: str,
        name_suffix: str,
        command: str | list[str] = "/sbin/init",
        network: Network | None = None,
        aliases: list[str] | None = None,
        environment: dict[str, str] | None = None,
        ports: dict[str, object] | None = None,
    ) -> Container:
        container_name = f"{self.resources.name}-{name_suffix}-{uuid4().hex[:8]}"
        run_kwargs = {
            "image": image_tag,
            "name": container_name,
            "command": command,
            "detach": True,
            "privileged": True,
            "tmpfs": {"/run": "", "/run/lock": ""},
            "environment": environment,
            "ports": ports,
            "labels": self.resources.labels,
            "log_config": LogConfig(type="json-file", config={"max-size": "10m", "max-file": "2"}),
        }
        try:
            container = self.client.containers.run(cgroupns="host", **run_kwargs)
        except TypeError:
            container = self.client.containers.run(**run_kwargs)
        except (APIError, DockerException) as error:
            raise AssertionError(f"Failed to start container from {image_tag}") from error

        self.containers.append(container)
        if network is not None:
            try:
                network.connect(container, aliases=aliases)
            except (APIError, DockerException) as error:
                raise AssertionError(
                    f"Failed to connect {container_name} to {network.name}"
                ) from error

        self.exec(container, "true")
        return container

    def put_file(self, container: Container, source: Path, destination: str) -> None:
        data = source.read_bytes()
        archive = BytesIO()
        destination_path = Path(destination)
        parent = str(destination_path.parent)

        with tarfile.open(fileobj=archive, mode="w") as tar:
            info = tarfile.TarInfo(name=destination_path.name)
            info.size = len(data)
            info.mode = 0o755
            info.mtime = int(time.time())
            tar.addfile(info, BytesIO(data))

        archive.seek(0)
        if not container.put_archive(parent, archive.getvalue()):
            raise AssertionError(f"Failed to copy {source} to {destination}")

    def exec(
        self,
        container: Container,
        command: str,
        env: dict[str, str] | None = None,
    ) -> ExecResult:
        try:
            result = container.exec_run(
                ["bash", "-lc", command],
                environment=env,
                demux=False,
            )
        except (APIError, DockerException) as error:
            raise AssertionError(f"Failed to exec command in container: {command}") from error

        output = result.output.decode("utf-8", errors="replace")
        exec_result = ExecResult(exit_code=result.exit_code, output=output)
        if exec_result.exit_code != 0:
            raise AssertionError(
                f"Command failed with exit code {exec_result.exit_code}: {command}\n"
                f"{exec_result.output}"
            )
        return exec_result

    def assert_files_exist(
        self, container: Container, paths: Iterable[str | Path]
    ) -> None:
        """Assert that each specified path is a regular file in the container."""
        for path in paths:
            quoted_path = shlex.quote(str(path))
            try:
                self.exec(container, f"test -f {quoted_path}")
            except AssertionError as error:
                raise AssertionError(f"Missing file in {container.name}: {path}") from error

    def cleanup(self) -> None:
        errors: list[str] = []
        for container in reversed(self.containers):
            try:
                container.remove(force=True, v=True)
            except NotFound:
                pass
            except DockerException as error:
                errors.append(str(error))

        for network in reversed(self.networks):
            try:
                network.remove()
            except NotFound:
                pass
            except DockerException as error:
                errors.append(str(error))

        self.client.close()
        if errors:
            raise RuntimeError("Docker test cleanup failed:\n" + "\n".join(errors))
