from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from docker.models.containers import Container

from __tests__.docker_test_utils import DockerTestRunner, ExecResult


def test_assert_files_exist_checks_arbitrary_paths_and_identifies_missing_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = DockerTestRunner.__new__(DockerTestRunner)
    container = cast(Container, SimpleNamespace(name="target"))
    commands: list[str] = []

    def fake_exec(_container: Container, command: str) -> ExecResult:
        commands.append(command)
        if "missing.py" in command:
            raise AssertionError("test -f failed")
        return ExecResult(exit_code=0, output="")

    monkeypatch.setattr(runner, "exec", fake_exec)

    runner.assert_files_exist(container, [Path("/opt/blitz/a file.py")])
    assert commands == ["test -f '/opt/blitz/a file.py'"]

    with pytest.raises(AssertionError, match="Missing file in target: /opt/blitz/missing.py"):
        runner.assert_files_exist(container, ["/opt/blitz/missing.py"])
