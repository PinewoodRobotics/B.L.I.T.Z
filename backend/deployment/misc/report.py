"""Readable, non-interactive deployment progress with complete remote logs."""
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import re
import time

from backend.deployment.compilation.util.systems import SystemId

_remote_log: ContextVar[Path | None] = ContextVar("remote_log", default=None)


def profile(system_id: SystemId) -> str:
    return (f"{system_id.linux_distro.value} / {system_id.architecture.value} / "
            f"Python {system_id.python_version.major}.{system_id.python_version.minor}")


@contextmanager
def stage(label: str, log_path: Path | None = None) -> Iterator[None]:
    started = time.monotonic()
    print(f"[RUN ] {label}", flush=True)
    token = _remote_log.set(log_path)
    try:
        if log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("")
        yield
    except BaseException:
        print(f"[FAIL] {label} ({time.monotonic() - started:.1f}s)", flush=True)
        if log_path is not None:
            print(f"       Full log: {log_path}", flush=True)
        raise
    else:
        print(f"[ OK ] {label} ({time.monotonic() - started:.1f}s)", flush=True)
    finally:
        _remote_log.reset(token)


def remote_output(output: str, returncode: int, attempt: int) -> bool:
    path = _remote_log.get()
    if path is None:
        return False
    with path.open("a") as log:
        log.write(f"\n--- attempt {attempt}; exit {returncode} ---\n{output}\n")
    import os
    if os.environ.get("BLITZ_VERBOSE") == "1":
        print(output, end="" if output.endswith("\n") else "\n", flush=True)
    elif returncode:
        print(f"[FAIL] Remote command exited {returncode}; last 25 lines:", flush=True)
        for line in output.splitlines()[-25:]:
            print(f"       {line}", flush=True)
    else:
        for line in dict.fromkeys(output.splitlines()):
            if re.search(r"\bwarning\b", line, re.IGNORECASE):
                print(f"[WARN] {line.strip()}", flush=True)
    return True
