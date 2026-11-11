import json
from pathlib import Path
import subprocess

import pytest

from backend.deployment.compilation.system_builder import SystemBuilder
from backend.deployment.compilation.util.cpp_build import CPPBuildConfig
from backend.deployment.compilation.util.systems import (
    Architecture,
    LinuxDistro,
    PythonVersion,
    SystemId,
)
from backend.deployment.module.supported import CPPLibraryModule, PythonModule, RustModule
from backend.deployment.network_api.utils import FolderPath


def test_system_build_key_round_trip_for_container_registry_distro() -> None:
    system = SystemId(
        "2.35", LinuxDistro.JETPACK_L4T_R36_2,
        Architecture.AARCH64, PythonVersion(3, 10),
    )
    assert SystemId.from_build_key(system.to_build_key()) == system


def test_one_system_graph_builds_every_declared_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    modules = []
    for name in ("motor", "sensor"):
        source = tmp_path / name
        source.mkdir()
        (source / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.20)\n")
        modules.append(CPPLibraryModule(name, FolderPath(str(source)), CPPBuildConfig("true")))
    rust_source = tmp_path / "telemetry"
    rust_source.mkdir()
    (rust_source / "Cargo.toml").write_text('[package]\nname = "telemetry"\nversion = "0.1.0"\n')
    modules.append(RustModule("telemetry", [], None, FolderPath(str(rust_source)), "telemetry"))
    python_source = tmp_path / "control"
    python_source.mkdir()
    (python_source / "__main__.py").write_text("print('ok')\n")
    modules.append(PythonModule("control", [], None, FolderPath(str(python_source))))
    (tmp_path / "requirements.txt").write_text("six==1.17.0\n")
    monkeypatch.chdir(tmp_path)

    calls: list[list[str]] = []

    def fake_run(command: list[str], _label: str, **_kwargs: object) -> str:
        calls.append(list(command))
        return "container-id\n" if command[1] == "create" else ""

    monkeypatch.setattr("backend.deployment.compilation.system_builder.run_command", fake_run)
    monkeypatch.setattr(SystemBuilder, "dependencies_cached", lambda _self: True)
    system_id = SystemId("2.36", LinuxDistro.DEBIAN_12, Architecture.AMD64, PythonVersion(3, 11))
    builder = SystemBuilder(
        system_id,
        FolderPath(str(tmp_path / "artifacts" / "bundle")),
        FolderPath(str(tmp_path / "contexts" / "bundle")),
    )
    builder.build(modules, bundle_dependencies=True)

    assert [call[1:3] for call in calls] == [["build", "--progress=plain"], ["image", "ls"]]
    assert calls[0][calls[0].index("--platform") + 1] == "linux/amd64"
    dockerfile = builder.dockerfile.read_text()
    assert dockerfile.startswith("ARG DEPENDENCY_IMAGE=scratch\n# dependency-cache: blitz-deps-")
    assert (
        "FROM --platform=linux/amd64 debian:12 AS dependencies\n"
        "WORKDIR /work\n"
        "COPY provision-plan.json build_system.sh /work/\n"
        "COPY dependency-inputs /work/dependency-inputs\n"
        "RUN /bin/bash /work/build_system.sh provision\n"
        "FROM ${DEPENDENCY_IMAGE} AS build\n"
        "COPY build_system.sh /work/build_system.sh\n"
        "COPY build_artifacts.py /work/build_artifacts.py\n"
        "COPY build-plan.json /work/build-plan.json\n"
        "COPY sources /work/sources\n"
        "COPY workspace /work/workspace\n"
    ) in dockerfile
    assert "RUN --network=none /bin/bash /work/build_system.sh compile\n" in dockerfile
    assert dockerfile.endswith("/bin/bash /work/build_system.sh compile\nFROM scratch AS artifacts\nCOPY --from=build /artifacts/ /\n")
    provision = json.loads((builder.context / "provision-plan.json").read_text())
    assert [step["kind"] for step in provision["steps"]] == [
        "system-packages", "cpp-dependencies", "cpp-dependencies", "rust-toolchain", "rust-fetch", "python-wheels"
    ]
    manifest = json.loads((builder.context / "build-plan.json").read_text())
    steps = manifest["steps"]
    ids = [step["id"] for step in steps]
    assert ids == [
        "system-packages", "cpp-dependencies:motor", "cpp-dependencies:sensor",
        "rust-toolchain", "rust-fetch:telemetry", "python-wheels",
        "cpp-build:motor", "cpp-build:sensor", "rust-build:telemetry",
        "copy:python:control", "native-libraries",
    ]
    assert next(step for step in steps if step["id"] == "cpp-build:motor")["requires"] == [
        "cpp-dependencies:motor", "cpp-dependencies:sensor"
    ]
    assert next(step for step in steps if step["id"] == "python-wheels")["requires"] == [
        "system-packages", "cpp-dependencies:motor", "cpp-dependencies:sensor"
    ]
    assert (builder.context / "workspace" / "telemetry" / "Cargo.toml").exists()
    assert (builder.context / "dependency-inputs" / "rust" / "telemetry" / "src" / "main.rs").exists()
    assert (builder.context / "dependency-inputs" / "python" / "requirements.txt").read_text() == "six==1.17.0\n"
    assert (builder.context / "sources" / "python" / "control" / "__main__.py").exists()
    assert (builder.context / "workspace" / "requirements.txt").read_text() == "six==1.17.0\n"
    dependency_image = builder.dependency_image()
    dockerfile_mtime = builder.dockerfile.stat().st_mtime_ns

    provision_before = (builder.context / "provision-plan.json").read_bytes()
    (python_source / "__main__.py").write_text("print('changed')\n")
    builder.prepare(modules, bundle_dependencies=True)
    assert (builder.context / "provision-plan.json").read_bytes() == provision_before
    assert (builder.context / "sources" / "python" / "control" / "__main__.py").read_text() == "print('changed')\n"
    assert builder.dependency_image() == dependency_image
    assert builder.dockerfile.stat().st_mtime_ns == dockerfile_mtime

    logging_script = tmp_path / "logging_build_system.sh"
    logging_script.write_text((builder.context / "build_system.sh").read_text() + "\n# More compile logging\n")
    monkeypatch.setattr("backend.deployment.compilation.system_builder.SCRIPT_PATH", logging_script)
    builder.prepare(modules, bundle_dependencies=True)
    assert builder.dependency_image() == dependency_image
    assert builder.dockerfile.stat().st_mtime_ns == dockerfile_mtime
    assert (builder.context / "build_system.sh").read_text().endswith("# More compile logging\n")

    (tmp_path / "requirements.txt").write_text("six==1.16.0\n")
    builder.prepare(modules, bundle_dependencies=True)
    assert builder.dependency_image() != dependency_image
    assert builder.dockerfile.stat().st_mtime_ns != dockerfile_mtime

    prepared_dockerfile = builder.dockerfile.read_bytes()
    monkeypatch.setattr(builder, "create_plan", lambda *_args: pytest.fail("regenerated Dockerfile"))
    calls.clear()
    builder.build_prepared()
    build = calls[0]
    assert build[:2] == ["docker", "build"]
    assert build[build.index("--target") + 1] == "artifacts"
    assert build[build.index("--output") + 1] == f"type=local,dest={builder.build_path}"
    # Artifacts are exported directly: no image is tagged or extracted from.
    assert "-t" not in build
    assert [call[:3] for call in calls[1:]] == [["docker", "image", "ls"]]
    assert builder.dockerfile.read_text().endswith(
        "FROM scratch AS artifacts\nCOPY --from=build /artifacts/ /\n"
    )
    assert builder.dockerfile.read_bytes() == prepared_dockerfile

    old_image = f"blitz-deps-{system_id.to_build_key()}-older"
    monkeypatch.setattr(SystemBuilder, "dependencies_cached", lambda _self: pytest.fail("checked current image"))
    calls.clear()
    builder.build_prepared(dependency_image=old_image)
    assert f"DEPENDENCY_IMAGE={old_image}" in calls[0]


def test_stale_dependency_images_match_only_the_current_system(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    system_id = SystemId("2.36", LinuxDistro.DEBIAN_12, Architecture.AMD64, PythonVersion(3, 11))
    builder = SystemBuilder(
        system_id,
        FolderPath(str(tmp_path / "artifacts")),
        FolderPath(str(tmp_path / "context")),
    )
    builder.prepare([], bundle_dependencies=False)
    current = builder.dependency_image()
    older = f"blitz-deps-{system_id.to_build_key()}-older"
    other_system = "blitz-deps-2.39-aarch64-ubuntu-24-04-python3-12-older"

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["docker", "image", "ls", "--format", "{{.Repository}}"]
        return subprocess.CompletedProcess(
            command, 0, f"{current}\n{older}\n{other_system}\n{older}\n", ""
        )

    monkeypatch.setattr("backend.deployment.compilation.system_builder.subprocess.run", fake_run)
    assert builder.stale_dependency_images() == [older]


@pytest.mark.parametrize('cached', [True, False])
def test_cleanup_requires_replacement_and_only_removes_owned_profile_images(tmp_path, monkeypatch, cached):
    system = SystemId('2.36', LinuxDistro.DEBIAN_12, Architecture.AMD64, PythonVersion(3, 11))
    builder = SystemBuilder(system, FolderPath(str(tmp_path / 'artifacts')), FolderPath(str(tmp_path / 'context')))
    builder.prepare([], bundle_dependencies=False)
    prefix = f'blitz-deps-{system.to_build_key()}-'.lower()
    old = prefix + '0' * 16
    # A longer system profile must not match this profile merely by prefix.
    candidates = [old, prefix + 'cap-cuda12-' + '1' * 16, 'unrelated-image', prefix + 'manual-tag']
    monkeypatch.setattr(builder, 'dependencies_cached', lambda: cached)
    monkeypatch.setattr(builder, 'stale_dependency_images', lambda: candidates)
    commands = []
    monkeypatch.setattr('backend.deployment.compilation.system_builder.run_command', lambda command, *_args, **_kwargs: commands.append(command))
    if not cached:
        with pytest.raises(RuntimeError, match='before current dependencies'):
            builder.prune_stale_dependency_images()
        assert commands == []
    else:
        assert builder.prune_stale_dependency_images() == [old]
        assert commands == [['docker', 'image', 'rm', old]]


def test_cleanup_keeps_in_use_images_and_continues(tmp_path, monkeypatch, capsys):
    system = SystemId('2.36', LinuxDistro.DEBIAN_12, Architecture.AMD64, PythonVersion(3, 11))
    builder = SystemBuilder(system, FolderPath(str(tmp_path / 'artifacts')), FolderPath(str(tmp_path / 'context')))
    first = f'blitz-deps-{system.to_build_key()}-' + '0' * 16
    second = f'blitz-deps-{system.to_build_key()}-' + '1' * 16
    monkeypatch.setattr(builder, 'dependencies_cached', lambda: True)
    monkeypatch.setattr(builder, 'stale_dependency_images', lambda: [first, second])
    def remove(command, *_args, **_kwargs):
        if command[-1] == first:
            raise subprocess.CalledProcessError(1, command, output='image is used by a container')
    monkeypatch.setattr('backend.deployment.compilation.system_builder.run_command', remove)
    assert builder.prune_stale_dependency_images() == [second]
    assert f'Kept stale Docker image {first}' in capsys.readouterr().out


@pytest.mark.parametrize(
    ("qualified_found", "listed", "expected"),
    [(True, "", True), (False, "db1d5c2830b8\n", True), (False, "", False)],
)
def test_dependency_cache_survives_intermittent_short_name_misses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    qualified_found: bool, listed: str, expected: bool,
) -> None:
    """Docker Desktop can miss a short name that its image store still holds."""
    system_id = SystemId("2.36", LinuxDistro.DEBIAN_12, Architecture.AMD64, PythonVersion(3, 11))
    builder = SystemBuilder(system_id, FolderPath(str(tmp_path / "artifacts")), FolderPath(str(tmp_path / "context")))
    monkeypatch.setattr(builder, "dependency_image", lambda: "blitz-deps-test")
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[:3] == ["docker", "image", "inspect"]:
            if command[-1] == "docker.io/library/blitz-deps-test:latest" and qualified_found:
                return subprocess.CompletedProcess(command, 0, "sha256:abc\n", "")
            return subprocess.CompletedProcess(command, 1, "", f"Error: No such image: {command[-1]}")
        return subprocess.CompletedProcess(command, 0, listed, "")

    monkeypatch.setattr("backend.deployment.compilation.system_builder.subprocess.run", fake_run)
    assert builder.dependencies_cached() is expected
    assert commands[0][-1] == "blitz-deps-test:latest"
    if not qualified_found:
        assert commands[-1] == ["docker", "image", "ls", "--quiet", "--filter", "reference=blitz-deps-test"]


@pytest.mark.parametrize("in_use", [False, True])
def test_build_retires_legacy_build_image_without_forcing(tmp_path, monkeypatch, capsys, in_use):
    system = SystemId("2.36", LinuxDistro.DEBIAN_12, Architecture.AMD64, PythonVersion(3, 11))
    builder = SystemBuilder(system, FolderPath(str(tmp_path / "artifacts")), FolderPath(str(tmp_path / "context")))
    builder.prepare([], bundle_dependencies=False)
    legacy = f"blitz-build-{system.to_build_key()}".lower()
    calls: list[list[str]] = []

    def fake_run(command, *_args, **_kwargs):
        calls.append(list(command))
        if command[:3] == ["docker", "image", "ls"]:
            return "799a4e6eb657\n"
        if command[:3] == ["docker", "image", "rm"] and in_use:
            raise subprocess.CalledProcessError(1, command, output="image is being used by a container")
        return ""

    monkeypatch.setattr("backend.deployment.compilation.system_builder.run_command", fake_run)
    builder.build_prepared(dependency_image="blitz-deps-cached")
    assert calls[-1] == ["docker", "image", "rm", legacy]
    assert ("Kept legacy build image" in capsys.readouterr().out) is in_use
