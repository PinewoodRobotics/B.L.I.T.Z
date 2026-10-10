import shlex
import sys

from backend.deployment.module.base import RunnableModule
from watchdog.process_starter import OpenedProcess


class FakeRunDefinition:
    def get_name(self) -> str:
        return "camera"

    def get_weight(self) -> float:
        return 1.0


class FakeRunnableModule(RunnableModule):
    def get_language_name(self) -> str:
        return "fake"

    def get_run_command(self, _bundle_path: str) -> str:
        code = (
            "import sys; "
            "print('stdout line', flush=True); "
            "print('stderr line', file=sys.stderr, flush=True)"
        )
        return f"{shlex.quote(sys.executable)} -u -c {shlex.quote(code)}"


def test_start_module_leaves_stdout_and_stderr_attached_to_parent(capfd, tmp_path):
    (tmp_path / "fake" / "camera").mkdir(parents=True)
    process = OpenedProcess.start_module(
        FakeRunnableModule(
            name="camera",
            extra_run_args=[],
            equivalent_run_definition=FakeRunDefinition(),  # pyright: ignore[reportArgumentType]
        ),
        str(tmp_path),
        {},
    )

    assert process.wait(timeout=5) == 0
    captured = capfd.readouterr()

    assert "stdout line" in captured.out
    assert "stderr line" in captured.err


def test_start_module_uses_bundled_native_libraries(monkeypatch, capfd, tmp_path):
    (tmp_path / "fake" / "camera").mkdir(parents=True)
    class EnvironmentRunnableModule(FakeRunnableModule):
        def get_run_command(self, _bundle_path: str) -> str:
            code = "import os; print(os.environ['LD_LIBRARY_PATH'], flush=True)"
            return f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"

    monkeypatch.setenv("LD_LIBRARY_PATH", "/system/libraries")
    process = OpenedProcess.start_module(
        EnvironmentRunnableModule("camera", [], FakeRunDefinition()),  # pyright: ignore[reportArgumentType]
        str(tmp_path),
        {},
    )
    assert process.wait(timeout=5) == 0
    output = capfd.readouterr().out
    assert f"{tmp_path}/lib/camera:{tmp_path}/deps/native" in output
    assert "/system/libraries" not in output  # Host paths cannot select an unintended library.


def test_runtime_metadata_uses_environment_without_injected_flags(tmp_path, capfd):
    import json

    class MetadataModule(FakeRunnableModule):
        def get_run_command(self, _bundle_path: str) -> str:
            code = "import os, sys, json; print(json.dumps([sys.argv[1:], os.environ['BLITZ_SYSTEM_NAME']]))"
            return f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"

    (tmp_path / "fake" / "camera").mkdir(parents=True)
    module = MetadataModule("camera", [], FakeRunDefinition())
    process = OpenedProcess.start_module(module, str(tmp_path), {"system-name": "test-pi"})
    assert process.wait(timeout=5) == 0
    assert json.loads(capfd.readouterr().out.strip().splitlines()[-1]) == [[], "test-pi"]

    from backend.deployment.module.contracts import LaunchSettings

    module.launch = LaunchSettings(accepts_blitz_flags=True)
    process = OpenedProcess.start_module(module, str(tmp_path), {"system-name": "test-pi"})
    assert process.wait(timeout=5) == 0
    assert json.loads(capfd.readouterr().out.strip().splitlines()[-1]) == [["--system-name", "test-pi"], "test-pi"]


def test_python_loads_compiled_shared_library_without_blitz_flags(tmp_path, capfd):
    import shutil
    import subprocess

    import pytest

    from backend.deployment.module.supported import PythonModule
    from backend.deployment.module.contracts import PythonEntrypoint
    from backend.deployment.network_api.utils import FolderPath

    compiler = shutil.which("c++")
    if compiler is None:
        pytest.skip("A C++ compiler is needed to exercise shared-library loading")
    bundle = tmp_path / "backend"
    library_dir = bundle / "lib" / "vision"
    library_dir.mkdir(parents=True)
    source = tmp_path / "vision.cpp"
    source.write_text('extern "C" int add(int left, int right) { return left + right; }\n')
    mode = "-dynamiclib" if sys.platform == "darwin" else "-shared"
    subprocess.run([compiler, mode, "-fPIC", str(source), "-o", str(library_dir / "libvision.so")], check=True)
    python_dir = bundle / "python" / "control"
    python_dir.mkdir(parents=True)
    python_dir.joinpath("main.py").write_text(
        'import ctypes, os, sys\n'
        'from pathlib import Path\n'
        'assert sys.argv[1:] == []\n'
        'vision = ctypes.CDLL(str(Path(os.environ["BLITZ_LIB_DIR"]) / "vision/libvision.so"))\n'
        'vision.add.argtypes = [ctypes.c_int, ctypes.c_int]\n'
        'vision.add.restype = ctypes.c_int\n'
        'print(vision.add(20, 22), flush=True)\n'
    )
    interpreter = tmp_path / ".venv" / "bin" / "python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    module = PythonModule("control", [], FakeRunDefinition(), FolderPath(str(python_dir)), entrypoint=PythonEntrypoint(file="main.py"))
    process = OpenedProcess.start_module(module, str(bundle), {"blitz-path": str(tmp_path)})
    assert process.wait(timeout=5) == 0
    assert capfd.readouterr().out.strip().splitlines()[-1] == "42"
