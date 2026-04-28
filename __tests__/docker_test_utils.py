from __future__ import annotations

import tarfile
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import docker
from docker.errors import APIError, DockerException, ImageNotFound, NotFound
from docker.models.containers import Container
from docker.models.networks import Network


@dataclass(frozen=True)
class ExecResult:
    exit_code: int
    output: str


class DockerTestRunner:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.client = docker.from_env()
        self.images: list[str] = []
        self.containers: list[Container] = []
        self.networks: list[Network] = []

    def build_image(self, dockerfile: str, tag_prefix: str) -> str:
        image_tag = f"{tag_prefix}:{int(time.time() * 1000)}"
        logs: list[str] = []

        try:
            _image, build_logs = self.client.images.build(
                path=str(self.repo_root),
                dockerfile=dockerfile,
                tag=image_tag,
                rm=True,
                forcerm=True,
            )
            for chunk in build_logs:
                line = chunk.get("stream") or chunk.get("error") or ""
                if line:
                    logs.append(line.rstrip())
        except (APIError, DockerException) as error:
            log_text = "\n".join(logs[-80:])
            raise AssertionError(
                f"Failed to build {dockerfile} as {image_tag}.\n{log_text}"
            ) from error

        self.images.append(image_tag)
        return image_tag

    def create_network(self, name_suffix: str) -> Network:
        network_name = f"blitz-pytest-{name_suffix}-{int(time.time() * 1000)}"
        try:
            network = self.client.networks.create(network_name, driver="bridge")
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
    ) -> Container:
        container_name = f"blitz-pytest-{name_suffix}-{int(time.time() * 1000)}"
        run_kwargs = {
            "image": image_tag,
            "name": container_name,
            "command": command,
            "detach": True,
            "privileged": True,
            "tmpfs": {"/run": "", "/run/lock": ""},
            "environment": environment,
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

    def cleanup(self) -> None:
        for container in reversed(self.containers):
            try:
                container.remove(force=True)
            except NotFound:
                pass
            except APIError:
                pass

        for image_tag in reversed(self.images):
            try:
                self.client.images.remove(image=image_tag, force=True, noprune=False)
            except ImageNotFound:
                pass
            except APIError:
                pass

        for network in reversed(self.networks):
            try:
                network.remove()
            except NotFound:
                pass
            except APIError:
                pass

        self.client.close()
