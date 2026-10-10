"""Keep rebuilds on a provisioned target using its compatible protobuf compiler."""
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("mode", ["system", "venv", "override"])
def test_generate_selects_provisioned_compiler(tmp_path: Path, mode: str) -> None:
    (tmp_path / "Makefile").write_text((ROOT / "Makefile").read_text())
    tools = tmp_path / "bin"
    tools.mkdir()
    log = tmp_path / "compiler.log"
    for path, label in [(tools / "protoc", "system"), (tools / "custom-protoc", "override")]:
        path.write_text(f'#!/bin/sh\nprintf "{label} %s\\n" "$*" > "$TEST_LOG"\n')
        path.chmod(0o755)
    if mode != "system":
        compiler = tmp_path / ".venv/bin/protoc"
        compiler.parent.mkdir(parents=True)
        compiler.write_text('#!/bin/sh\nprintf "venv %s\\n" "$*" > "$TEST_LOG"\n')
        compiler.chmod(0o755)
    command = ["make", "generate"]
    if mode == "override":
        command.append(f"PROTOC={tools / 'custom-protoc'}")
    subprocess.run(command, cwd=tmp_path,
                   env=dict(os.environ, PATH=f"{tools}:{os.environ['PATH']}", TEST_LOG=str(log)),
                   check=True, capture_output=True)
    output = log.read_text()
    assert output.startswith(mode + " ")
    assert "--pyi_out=watchdog/generated" in output
    assert "proto/PiStatus.proto" in output
