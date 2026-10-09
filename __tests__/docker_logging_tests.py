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
    assert "#1 [build] RUN compile" in visible
    assert "[blitz] START step=cpp-build:motor" in visible
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
