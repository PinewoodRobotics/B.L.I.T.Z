import os
from pathlib import Path
import re
import subprocess
import time
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

    started = time.monotonic()
    if on_output is not None:
        on_output(label)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            display_log = log_path.relative_to(Path.cwd())
        except ValueError:
            display_log = log_path
        print(f"[RUN ] {label}\n       Log: {display_log}", flush=True)

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
            elif show_progress and "[blitz]" in clean_line:
                marker = clean_line.split("[blitz]", 1)[1].strip()
                step = re.search(r"\bstep=([^\s]+)", marker)
                status = marker.split()[0] if marker else ""
                if step and status in {"START", "DONE"}:
                    state = "run" if status == "START" else "ok"
                    print(f"       {state:>3}  {step.group(1)}", flush=True)
                else:
                    print(f"       {marker}", flush=True)
            elif show_progress and (
                re.search(r"\bwarning\b", clean_line, re.IGNORECASE)
                or re.match(r"^\s*- [A-Za-z]+:.*\(line ", clean_line)
            ):
                print(f"[WARN] {clean_line.strip()}", flush=True)
    finally:
        if log_file is not None:
            log_file.close()

    return_code = process.wait()
    output = "".join(output_lines)
    if return_code == 0:
        if log_path is not None:
            print(f"[ OK ] {label} ({time.monotonic() - started:.1f}s)", flush=True)
        return output

    tail = list(tail_lines)
    if on_failure is not None:
        on_failure(label, tail)
    else:
        print(f"[FAIL] {label}: exit {return_code} ({time.monotonic() - started:.1f}s)")
        if log_path is not None:
            print(f"Full command output: {log_path}")
        for line in tail:
            print(line)

    raise subprocess.CalledProcessError(return_code, command, output=output)
