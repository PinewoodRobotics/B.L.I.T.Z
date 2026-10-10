"""Own Docker build storage for one pytest session, without pruning other projects."""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
import json
import re
import shutil
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory, gettempdir
from uuid import uuid4

from backend.deployment.compilation.util.commands import run_command


class DockerTestResources:
    """Use a disposable BuildKit volume and uniquely named test images."""

    def __init__(self) -> None:
        self.name = f"blitz-pytest-{uuid4().hex}"
        self.labels = {"blitz.pytest.session": self.name}
        self.images: dict[str, str] = {}
        self.layouts: dict[str, Path] = {}
        self.installation_images: dict[tuple[Path, str], str] = {}
        self._directory = TemporaryDirectory(prefix=f"{self.name}-")
        self.root = Path(self._directory.name)
        (self.root / "session.json").write_text(json.dumps({"session": self.name}))
        self._builder_created = False

    def image_name(self, image: str) -> str:
        if image.startswith(f"{self.name}-"):
            return image
        return self.images.setdefault(image, f"{self.name}-{image}")

    def _ensure_builder(self) -> None:
        if self._builder_created:
            return
        # Register before launching so teardown also handles partial setup.
        self._builder_created = True
        run_command(
            ["docker", "buildx", "create", "--name", self.name,
             "--driver", "docker-container"],
            "Create isolated pytest Docker builder",
        )

    def build(self, arguments: Sequence[str], label: str, **kwargs: object) -> str:
        self._ensure_builder()
        arguments = list(arguments)
        tag = arguments[arguments.index("-t") + 1]
        extra = ["--builder", self.name, "--load", "--provenance=false",
                 "--label", f"blitz.pytest.session={self.name}"]
        # BuildKit runs separately from Docker's image store. Export dependencies
        # as a local OCI layout too, then supply that exact image to offline builds.
        # This preserves the real Dockerfile and never needs a local registry.
        if "--target" in arguments and arguments[arguments.index("--target") + 1] == "dependencies":
            layout = self.root / hashlib.sha256(tag.encode()).hexdigest()
            extra += ["--output", f"type=oci,dest={layout},tar=false"]
            self.layouts[tag] = layout
        for index, value in enumerate(arguments):
            if value.startswith("DEPENDENCY_IMAGE="):
                image = value.split("=", 1)[1]
                layout = self.layouts[image]
                manifest = json.loads((layout / "index.json").read_text())["manifests"][0]["digest"]
                arguments[index] = "DEPENDENCY_IMAGE=pytest-dependencies"
                extra += ["--build-context", f"pytest-dependencies=oci-layout://{layout}@{manifest}"]
        try:
            return run_command(["docker", "buildx", "build", *extra, *arguments], label, **kwargs)
        finally:
            # Keep a small reusable cache within the session. Only this builder's
            # cache is touched; teardown deletes its complete volume.
            run_command(
                ["docker", "buildx", "prune", "--builder", self.name,
                 "--force", "--keep-storage", "4GB"],
                "Limit pytest Docker build cache",
            )

    def run(self, command: Sequence[str], label: str, **kwargs: object) -> str:
        """Adapt SystemBuilder commands only while a Docker test fixture is active."""
        command = list(command)
        if command[:2] == ["docker", "build"]:
            index = command.index("-t") + 1
            command[index] = self.image_name(command[index])
            return self.build(command[2:], label, **kwargs)
        if command[:2] == ["docker", "create"]:
            command = [self.images.get(argument, argument) for argument in command]
            command[2:2] = ["--label", f"blitz.pytest.session={self.name}"]
        return run_command(command, label, **kwargs)

    def installation_image(self, repo_root: Path, dockerfile: str) -> str:
        key = (repo_root.resolve(), dockerfile)
        if key not in self.installation_images:
            image = self.image_name(Path(dockerfile).name.lower())
            self.build(
                ["--progress=plain", "-f", str(repo_root / dockerfile), "-t", image, str(repo_root)],
                f"Build pytest installation image {dockerfile}", show_progress=True,
            )
            self.installation_images[key] = image
        return self.installation_images[key]

    def cleanup(self) -> None:
        try:
            if self._builder_created:
                cleanup_session(self.name, remove_builder=True)
        finally:
            self._directory.cleanup()


def cleanup_session(name: str, *, remove_builder: bool) -> None:
    """Delete only a session's builder and explicitly labeled Docker resources."""
    if not re.fullmatch(r"blitz-pytest-[0-9a-f]{32}", name):
        raise ValueError(f"Invalid Docker test session: {name}")
    import docker

    errors: list[str] = []
    if remove_builder:
        result = subprocess.run(
            ["docker", "buildx", "rm", "--force", name],
            capture_output=True, text=True,
        )
        if result.returncode:
            errors.append(result.stderr.strip())
    client = docker.from_env()
    filters = {"label": f"blitz.pytest.session={name}"}
    try:
        for container in client.containers.list(all=True, filters=filters):
            try:
                container.remove(force=True, v=True)
            except docker.errors.DockerException as error:
                errors.append(str(error))
        # IDs catch dangling images after failures and after a tag is overwritten.
        for image_id in dict.fromkeys(image.id for image in client.images.list(all=True, filters=filters)):
            try:
                client.images.remove(image_id, force=True)
            except docker.errors.DockerException as error:
                errors.append(str(error))
        for network in client.networks.list(filters=filters):
            try:
                network.remove()
            except docker.errors.DockerException as error:
                errors.append(str(error))
    finally:
        client.close()
    if errors:
        raise RuntimeError("Docker test cleanup failed:\n" + "\n".join(errors))


def cleanup_leftovers() -> None:
    """Manual recovery after hard termination; stop Docker test runs first."""
    import docker

    result = subprocess.run(
        ["docker", "buildx", "ls", "--format", "{{.Name}}"],
        capture_output=True, text=True, check=True,
    )
    builders = {name for name in result.stdout.splitlines() if re.fullmatch(r"blitz-pytest-[0-9a-f]{32}", name)}
    sessions = set(builders)
    client = docker.from_env()
    try:
        filters = {"label": "blitz.pytest.session"}
        for image in client.images.list(all=True, filters=filters):
            sessions.add(image.labels["blitz.pytest.session"])
        for container in client.containers.list(all=True, filters=filters):
            sessions.add(container.labels["blitz.pytest.session"])
        for network in client.networks.list(filters=filters):
            sessions.add(network.attrs["Labels"]["blitz.pytest.session"])
    finally:
        client.close()
    directories: dict[Path, str] = {}
    for path in Path(gettempdir()).glob("blitz-pytest-*"):
        if path.is_symlink() or not path.is_dir():
            continue
        try:
            name = json.loads((path / "session.json").read_text())["session"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if (
            isinstance(name, str)
            and re.fullmatch(r"blitz-pytest-[0-9a-f]{32}", name)
            and path.name.startswith(f"{name}-")
        ):
            directories[path] = name
            sessions.add(name)
    for name in sorted(sessions):
        if re.fullmatch(r"blitz-pytest-[0-9a-f]{32}", name):
            cleanup_session(name, remove_builder=name in builders)
            print(f"Removed Docker test session {name}")
    for path in directories:
        shutil.rmtree(path)
    if not sessions:
        print("No Docker test leftovers found.")


if __name__ == "__main__":
    cleanup_leftovers()
