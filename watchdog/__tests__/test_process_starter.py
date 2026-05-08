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


def test_start_module_leaves_stdout_and_stderr_attached_to_parent(capfd):
    process = OpenedProcess.start_module(
        FakeRunnableModule(
            name="camera",
            extra_run_args=[],
            equivalent_run_definition=FakeRunDefinition(),  # pyright: ignore[reportArgumentType]
        ),
        "unused",
        {},
    )

    assert process.wait(timeout=5) == 0
    captured = capfd.readouterr()

    assert "stdout line" in captured.out
    assert "stderr line" in captured.err
