"""Verify disk retention against real pytest sessions, including concurrent runs."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time


CONFIG = Path(__file__).resolve().parents[1] / "pyproject.toml"


def child_environment(root: Path) -> dict[str, str]:
    root.mkdir()
    environment = dict(os.environ, PYTEST_DEBUG_TEMPROOT=str(root), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    environment.pop("PYTEST_ADDOPTS", None)
    return environment


def pytest_command(source: Path) -> list[str]:
    return [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-c", str(CONFIG), str(source)]


def test_concurrent_sessions_preserve_active_files_and_discard_successful_runs(tmp_path: Path) -> None:
    shared = tmp_path / "temporary-runs"
    environment = child_environment(shared)
    ready, release = tmp_path / "ready", tmp_path / "release"
    first = tmp_path / "first_tests.py"
    first.write_text(
        "from pathlib import Path\nimport time\n"
        "def test_active_files(tmp_path):\n"
        "    marker = tmp_path / 'marker'\n"
        "    marker.write_text('keep while active')\n"
        f"    Path({str(ready)!r}).write_text(str(marker))\n"
        "    deadline = time.monotonic() + 20\n"
        f"    while not Path({str(release)!r}).exists():\n"
        "        assert time.monotonic() < deadline\n"
        "        time.sleep(0.02)\n"
        "    assert marker.read_text() == 'keep while active'\n"
    )
    second = tmp_path / "second_tests.py"
    second.write_text("def test_new_session(tmp_path):\n    (tmp_path / 'marker').write_text('temporary')\n")
    process = subprocess.Popen(pytest_command(first), cwd=tmp_path, env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        deadline = time.monotonic() + 10
        while not ready.exists():
            assert process.poll() is None, "First pytest session exited before its test started"
            assert time.monotonic() < deadline, "First pytest session did not start"
            time.sleep(0.02)
        marker = Path(ready.read_text())
        assert (marker.parent.parent / ".lock").is_file()
        result = subprocess.run(pytest_command(second), cwd=tmp_path, env=environment,
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stdout + result.stderr
        assert marker.is_file(), "Concurrent cleanup deleted active test files"
    finally:
        release.touch()
        output, _ = process.communicate(timeout=10)
    assert process.returncode == 0, output
    assert not marker.exists()
    assert not list(shared.rglob("marker"))


def test_repeated_failures_retain_only_one_session(tmp_path: Path) -> None:
    shared = tmp_path / "temporary-runs"
    environment = child_environment(shared)
    source = tmp_path / "failure_tests.py"
    source.write_text(
        "def test_failed_artifacts(tmp_path):\n"
        "    (tmp_path / 'marker').write_text('failure diagnostics')\n"
        "    assert False, 'intentional failure'\n"
    )
    for _ in range(2):
        result = subprocess.run(pytest_command(source), cwd=tmp_path, env=environment,
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 1, result.stdout + result.stderr
    assert len(list(shared.rglob("marker"))) == 1
