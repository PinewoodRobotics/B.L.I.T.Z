from generated.Startup_pb2 import ProcessType
import subprocess
from typing import Optional, List


def start_process(process_type: ProcessType, config_path: str):
    args = [construct_argument("--config", config_path)]
    match process_type:
        case ProcessType.POS_EXTRAPOLATOR:
            return start_process_make("position-extrapolator", args)
        case ProcessType.LIDAR_PROCESSING:
            return start_process_make("lidar-processing", args)
        case ProcessType.CAMERA_PROCESSING:
            return start_process_make("april-server", args)
        case _:
            raise ValueError(f"Unknown process type: {process_type}")


def construct_argument(main_name: str, arg_value: str) -> str:
    return f"{main_name} {arg_value}"


def start_process_make(process_name: str, extra_args: Optional[List[str]] = None):
    try:
        args_str = f'ARGS="{" ".join(extra_args)}"' if extra_args else ""
        cmd = ["make", process_name]
        if args_str:
            cmd.extend([args_str])

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            shell=True,
        )

        return process
    except subprocess.SubprocessError as e:
        print(f"Failed to start position extrapolator: {str(e)}")
        return None
