from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from __tests__.docker_resources import DockerTestResources, cleanup_leftovers, cleanup_session


@pytest.fixture
def resources() -> Iterator[DockerTestResources]:
    resources = DockerTestResources()
    yield resources
    # These unit tests mock Docker; they should never contact a real daemon.
    resources._directory.cleanup()


def test_installation_images_are_reused_and_cache_pruning_is_scoped(resources, tmp_path, monkeypatch):
    commands = []
    monkeypatch.setattr("__tests__.docker_resources.run_command", lambda command, *_args, **_kwargs: commands.append(command) or "")
    first = resources.installation_image(tmp_path, "docker/Dockerfile.dev.test")
    assert resources.installation_image(tmp_path, "docker/Dockerfile.dev.test") == first
    assert len(commands) == 3
    assert commands[0] == ["docker", "buildx", "create", "--name", resources.name, "--driver", "docker-container"]
    assert "--use" not in commands[0]
    assert commands[1][:5] == ["docker", "buildx", "build", "--builder", resources.name]
    assert commands[1][commands[1].index("-t") + 1].startswith(resources.name)
    assert commands[2] == ["docker", "buildx", "prune", "--builder", resources.name, "--force", "--keep-storage", "4GB"]


def test_offline_build_uses_exact_exported_dependencies_without_editing_dockerfile(resources, tmp_path, monkeypatch):
    commands = []

    def run(command, *_args, **_kwargs):
        commands.append(command)
        for argument in command:
            if argument.startswith("type=oci,"):
                layout = Path(argument.split("dest=", 1)[1].split(",", 1)[0])
                layout.mkdir()
                (layout / "index.json").write_text(json.dumps({"manifests": [{"digest": "sha256:abc"}]}))
        return ""

    monkeypatch.setattr("__tests__.docker_resources.run_command", run)
    image = resources.image_name("blitz-deps-profile-hash")
    resources.run(["docker", "build", "--target", "dependencies", "-t", image, str(tmp_path)], "Cache")
    assert resources.image_name(image) == image
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("ARG DEPENDENCY_IMAGE=scratch\nFROM ${DEPENDENCY_IMAGE} AS build\n")
    original = dockerfile.read_bytes()
    resources.run(["docker", "build", "--network", "none", "--build-arg", f"DEPENDENCY_IMAGE={image}",
                   "-f", str(dockerfile), "-t", "blitz-build-profile", str(tmp_path)], "Build")
    build = commands[-2]
    assert "DEPENDENCY_IMAGE=pytest-dependencies" in build
    assert build[build.index("--build-context") + 1] == f"pytest-dependencies=oci-layout://{resources.layouts[image]}@sha256:abc"
    assert build[build.index("--network") + 1] == "none"
    assert dockerfile.read_bytes() == original
    resources.run(["docker", "create", "blitz-build-profile"], "Create")
    assert commands[-1][-1] == resources.image_name("blitz-build-profile")


def test_failed_build_still_limits_its_cache(resources, tmp_path, monkeypatch):
    commands = []

    def run(command, *_args, **_kwargs):
        commands.append(command)
        if command[:3] == ["docker", "buildx", "build"]:
            raise subprocess.CalledProcessError(1, command)
        return ""

    monkeypatch.setattr("__tests__.docker_resources.run_command", run)
    with pytest.raises(subprocess.CalledProcessError):
        resources.installation_image(tmp_path, "Dockerfile")
    assert commands[-1][:3] == ["docker", "buildx", "prune"]
    assert commands[-1][commands[-1].index("--builder") + 1] == resources.name
    assert resources.installation_images == {}


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_cleanup_removes_only_session_resources_and_reports_errors(resources, monkeypatch, cleanup_fails):
    resources._builder_created = True
    commands = []
    monkeypatch.setattr("__tests__.docker_resources.subprocess.run", lambda command, **_kwargs:
                        commands.append(command) or SimpleNamespace(returncode=0, stderr=""))
    client = MagicMock()
    container, image, network = MagicMock(), SimpleNamespace(id="owned-image"), MagicMock()
    client.containers.list.return_value = [container]
    client.images.list.return_value = [image]
    client.networks.list.return_value = [network]
    monkeypatch.setattr("docker.from_env", lambda: client)
    if cleanup_fails:
        from docker.errors import APIError

        client.images.remove.side_effect = APIError("cleanup refused")
        with pytest.raises(RuntimeError, match="cleanup refused"):
            resources.cleanup()
    else:
        resources.cleanup()
    assert commands == [["docker", "buildx", "rm", "--force", resources.name]]
    label = {"label": f"blitz.pytest.session={resources.name}"}
    client.images.list.assert_called_once_with(all=True, filters=label)
    client.containers.list.assert_called_once_with(all=True, filters=label)
    client.networks.list.assert_called_once_with(filters=label)
    container.remove.assert_called_once_with(force=True, v=True)
    client.images.remove.assert_called_once_with("owned-image", force=True)
    network.remove.assert_called_once_with()
    client.close.assert_called_once_with()
    assert not resources.root.exists()


def test_no_docker_resources_are_created_for_unit_tests(resources, monkeypatch):
    def unexpected(*_args, **_kwargs):
        raise AssertionError("Unit-only runs must not contact Docker")

    monkeypatch.setattr("__tests__.docker_resources.subprocess.run", unexpected)
    monkeypatch.setattr("docker.from_env", unexpected)
    resources.cleanup()
    assert not resources.root.exists()


def test_manual_cleanup_recovers_abandoned_sessions_and_preserves_other_resources(tmp_path, monkeypatch):
    session = "blitz-pytest-" + "a" * 32
    abandoned = tmp_path / f"{session}-directory"
    abandoned.mkdir()
    (abandoned / "session.json").write_text(json.dumps({"session": session}))
    unrelated = tmp_path / "blitz-pytest-unrelated-directory"
    unrelated.mkdir()
    (unrelated / "keep.txt").write_text("keep")
    monkeypatch.setattr("__tests__.docker_resources.gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr("__tests__.docker_resources.subprocess.run", lambda *_args, **_kwargs:
                        SimpleNamespace(stdout=f"default\n{session}\nother-project\n"))
    client = MagicMock()
    client.images.list.return_value = [SimpleNamespace(labels={"blitz.pytest.session": session})]
    client.containers.list.return_value = []
    client.networks.list.return_value = []
    monkeypatch.setattr("docker.from_env", lambda: client)
    cleaned = []
    monkeypatch.setattr("__tests__.docker_resources.cleanup_session", lambda name, **kwargs: cleaned.append((name, kwargs)))
    cleanup_leftovers()
    assert cleaned == [(session, {"remove_builder": True})]
    client.images.list.assert_called_once_with(all=True, filters={"label": "blitz.pytest.session"})
    assert not abandoned.exists()
    assert (unrelated / "keep.txt").read_text() == "keep"


def test_cleanup_rejects_non_test_builder_names(monkeypatch):
    def unexpected(*_args, **_kwargs):
        raise AssertionError("Must not contact Docker for non-test names")

    monkeypatch.setattr("__tests__.docker_resources.subprocess.run", unexpected)
    with pytest.raises(ValueError, match="Invalid Docker test session"):
        cleanup_session("desktop-linux", remove_builder=True)
