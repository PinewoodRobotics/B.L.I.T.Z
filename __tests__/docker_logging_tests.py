from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from backend.deployment.compilation.system_builder import DockerCacheInspectionError, SystemBuilder
from backend.deployment.compilation.util.systems import Architecture, LinuxDistro, PythonVersion, SystemId
from backend.deployment.compilation.util.commands import run_command
from backend.deployment.network_api.utils import FolderPath


def test_docker_progress_is_visible_and_full_output_is_saved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log_path = tmp_path / "logs" / "compile.log"
    output = run_command(
        [sys.executable, "-c", "print('#1 [build] RUN compile'); print('[blitz] START step=cpp-build:motor'); print('compiler detail')"],
        "Build target bundle", log_path=log_path, show_progress=True,
    )

    visible = capsys.readouterr().out
    assert "#1 [build] RUN compile" not in visible
    assert "run  cpp-build:motor" in visible
    assert "[RUN ] Build target bundle" in visible
    assert "[ OK ] Build target bundle" in visible
    assert "compiler detail" not in visible
    assert "compiler detail" in output
    assert "compiler detail" in log_path.read_text()


def test_failed_provision_step_names_module_and_keeps_log(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stubs = tmp_path / "bin"
    stubs.mkdir()
    (stubs / "apt-get").write_text("#!/bin/sh\nexit 0\n")
    (stubs / "ldd").write_text("#!/bin/sh\necho 'ldd (glibc) 2.36'\n")
    (stubs / "jq").write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "query = sys.argv[2].removeprefix('.')\n"
        "data = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else json.load(sys.stdin)\n"
        "if query == 'steps[]':\n"
        "    for step in data['steps']: print(json.dumps(step))\n"
        "else:\n"
        "    keys = query.split(' // ')[0].split('.')\n"
        "    for key in keys: data = data.get(key, '') if isinstance(data, dict) else ''\n"
        "    print(data)\n"
    )
    for executable in stubs.iterdir():
        executable.chmod(0o755)
    plan = tmp_path / "provision-plan.json"
    plan.write_text(json.dumps({
        "system": {"glibc": "2.36", "distro_key": "debian-12", "python_major": 3, "python_minor": 11},
        "steps": [{"id": "cpp-dependencies:motor", "kind": "cpp-dependencies", "module": "motor", "libraries": "false"}],
    }))
    log_path = tmp_path / "logs" / "dependencies.log"
    environment = os.environ.copy()
    environment["PATH"] = f"{stubs}:{environment['PATH']}"
    environment["BLITZ_PLAN_PATH"] = str(plan)
    script = Path(__file__).resolve().parents[1] / "backend/deployment/compilation/build_system.sh"

    with pytest.raises(subprocess.CalledProcessError):
        run_command(
            ["bash", str(script), "provision"], "Cache dependencies",
            env=environment, log_path=log_path, show_progress=True,
        )

    logged = log_path.read_text()
    assert "START phase=provision step=cpp-dependencies:motor kind=cpp-dependencies module=motor" in logged
    assert "FAILED phase=provision step=cpp-dependencies:motor kind=cpp-dependencies module=motor exit=1" in logged
    assert str(log_path) in capsys.readouterr().out


def test_docker_unavailable_is_not_reported_as_a_cache_miss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    system_id = SystemId("2.36", LinuxDistro.DEBIAN_12, Architecture.AMD64, PythonVersion(3, 11))
    builder = SystemBuilder(system_id, FolderPath(str(tmp_path / "artifacts")), FolderPath(str(tmp_path / "context")))
    monkeypatch.setattr(builder, "dependency_image", lambda: "blitz-deps-test")
    monkeypatch.setattr(
        "backend.deployment.compilation.system_builder.subprocess.run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", "Cannot connect to the Docker daemon"),
    )

    with pytest.raises(DockerCacheInspectionError, match="Docker daemon"):
        builder.dependencies_cached()


def test_remote_stage_preserves_logs_and_surfaces_warnings(tmp_path, capsys, monkeypatch):
    from backend.deployment.misc.report import remote_output, stage
    monkeypatch.delenv("BLITZ_VERBOSE", raising=False)
    path = tmp_path / "install.log"
    with stage("tripoli: install dependencies", path):
        assert remote_output("inflating hundreds of files\nWARNING: package conflict\n", 0, 1)
    visible = capsys.readouterr().out
    assert "inflating" not in visible
    assert "[WARN] WARNING: package conflict" in visible
    assert "[ OK ] tripoli: install dependencies" in visible
    assert "inflating hundreds of files" in path.read_text()
    assert not remote_output("outside deployment", 0, 1)


def test_failed_remote_stage_keeps_tail_and_restores_context(tmp_path, capsys):
    from backend.deployment.misc.report import remote_output, stage
    path = tmp_path / "failed.log"
    with pytest.raises(RuntimeError, match="install failed"):
        with stage("tripoli: install bundle", path):
            assert remote_output("\n".join(f"line {i}" for i in range(40)), 7, 3)
            raise RuntimeError("install failed")
    visible = capsys.readouterr().out
    assert "[FAIL] tripoli: install bundle" in visible
    assert "Remote command exited 7" in visible
    assert "line 39" in visible
    assert "       line 0\n" not in visible
    assert str(path) in visible
    assert "line 0\n" in path.read_text()
    assert not remote_output("outside deployment", 0, 1)


def test_verbose_commands_keep_raw_output(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("BLITZ_VERBOSE", "1")
    run_command([sys.executable, "-c", "print('raw compiler detail')"],
                "Compile", log_path=tmp_path / "compile.log")
    assert "raw compiler detail" in capsys.readouterr().out


def test_docker_warning_details_are_visible(tmp_path, capsys):
    warning = " - FromPlatformFlagConstDisallowed: constant platform (line 1)"
    run_command([sys.executable, "-c", f"print({warning!r})"], "Build",
                log_path=tmp_path / "build.log", show_progress=True)
    assert warning.strip() in capsys.readouterr().out


def test_build_log_path_is_short_and_profile_specific(tmp_path):
    first = SystemId("2.36", LinuxDistro.DEBIAN_12, Architecture.AMD64, PythonVersion(3, 11))
    builder = SystemBuilder(first, FolderPath(str(tmp_path / "artifacts")),
                            FolderPath(str(tmp_path / "contexts" / first.to_build_key())))
    path = builder._log_path("compile")
    assert len(path.parent.name) < 80
    assert "debian-12" in path.parent.name
    assert path.name == "compile.log"
