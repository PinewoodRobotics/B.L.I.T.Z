import os
from pathlib import Path
import re
import subprocess
from collections import deque
from collections.abc import Callable, Mapping, Sequence


ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
TAIL_LINES_ON_FAILURE = 25


def strip_ansi(value: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub("", value)


def verbose_enabled() -> bool:
    return os.environ.get("BLITZ_VERBOSE") == "1"


def run_command(
    command: Sequence[str],
    label: str,
    env: Mapping[str, str] | None = None,
    on_output: Callable[[str], None] | None = None,
    on_failure: Callable[[str, list[str]], None] | None = None,
    log_path: Path | None = None,
    show_progress: bool = False,
) -> str:
    """
    Run a subprocess while keeping UI concerns outside compilation code.

    The command output is captured and returned for flag parsing. Docker callers
    can also save the complete output and display build and plan step markers.
    """

    if on_output is not None:
        on_output(label)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"{label} (log: {log_path})", flush=True)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )

    output_lines: list[str] = []
    tail_lines: deque[str] = deque(maxlen=TAIL_LINES_ON_FAILURE)
    assert process.stdout is not None
    log_file = log_path.open("w") if log_path is not None else None
    try:
        for line in process.stdout:
            clean_line = strip_ansi(line)
            output_lines.append(clean_line)
            if log_file is not None:
                log_file.write(clean_line)
                log_file.flush()
            if clean_line.strip():
                tail_lines.append(clean_line.rstrip())
                if on_output is not None and not label.startswith("Prepare "):
                    on_output(clean_line)

            if verbose_enabled():
                print(clean_line, end="", flush=True)
            elif show_progress and (
                "[blitz]" in clean_line
                or re.match(r"^#\d+ (?:\[|DONE|CACHED|ERROR)", clean_line)
            ):
                print(clean_line, end="", flush=True)
    finally:
        if log_file is not None:
            log_file.close()

    return_code = process.wait()
    output = "".join(output_lines)
    if return_code == 0:
        return output

    tail = list(tail_lines)
    if on_failure is not None:
        on_failure(label, tail)
    else:
        print(f"{label} failed with exit code {return_code}")
        if log_path is not None:
            print(f"Full command output: {log_path}")
        for line in tail:
            print(line)

    raise subprocess.CalledProcessError(return_code, command, output=output)
