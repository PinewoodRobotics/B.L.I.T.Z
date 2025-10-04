from logging import debug, error, info
import subprocess
from typing import Optional, List
import sys
import os

from backend.python.common.util.system import ProcessType


def start_process(process_type: ProcessType, config_path: str):
    return start_process_make(process_type.value, ["--config", config_path])


def start_process_make(process_name: str, extra_args: Optional[List[str]] = None):
    try:
        env = os.environ.copy()
        if extra_args:
            env["ARGS"] = " ".join(extra_args)

        cmd = ["make", process_name]

        debug(f"Starting: {' '.join(cmd)} with ARGS={env.get('ARGS', '')}\n")

        return subprocess.Popen(
            cmd,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env,
        )
    except subprocess.SubprocessError as e:
        error(f"Failed to start {process_name}: {str(e)}")
        return None
