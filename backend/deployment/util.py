import dataclasses
from dataclasses import dataclass
from enum import Enum
from collections.abc import Sequence
import json
from typing import Callable, Mapping, Protocol
import inspect
import subprocess
import time
import os
import shutil

from backend.deployment.compilation_util import CPPBuildConfig
from backend.deployment import pi_api as _pi_api
from backend.deployment.pi_api import RaspberryPi as _RaspberryPi
from backend.deployment.system_types import (
    SystemType,
    get_self_architecture,
    get_self_ldd_version,
)


# Backwards-compatible aliases (discovery now lives in `deployment/pi_api.py`)
SERVICE = _pi_api.SERVICE
DISCOVERY_TIMEOUT = _pi_api.DISCOVERY_TIMEOUT
BACKEND_DEPLOYMENT_PATH = "/opt/blitz/B.L.I.T.Z/backend"
GITIGNORE_PATH = ".gitignore"
VENV_PATH = ".venv/bin/python"
LOCAL_BINARIES_PATH = "build/release/"
EXCLUDE_CPP_DIR = True
SHOULD_REBUILD_BINARIES = True
CONFIG_GET_COMMAND = "npm run config --silent"


def _get_config() -> str:
    try:
        result = subprocess.run(
            CONFIG_GET_COMMAND.split(), capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to run '{CONFIG_GET_COMMAND}': {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON output from '{CONFIG_GET_COMMAND}': {e}")


@dataclass
class _Module:
    pass


@dataclass
class _CompilableModule(_Module):
    project_root_folder_path: str
    build_for_platforms: list[SystemType]


@dataclass
class _RunnableModule(_Module):
    extra_run_args: list[tuple[str, str]]
    equivalent_run_definition: str

    def get_run_command(self) -> str:
        return ""

    def get_lang_folder_name(self) -> str:
        if isinstance(self, ModuleTypes.PythonModule):
            return "python"
        elif isinstance(self, ModuleTypes.RustModule):
            return "rust"
        elif isinstance(self, ModuleTypes.ProtobufModule):
            return "proto"
        elif isinstance(self, ModuleTypes.ThriftModule):
            return "thrift"
        else:
            raise ValueError(f"Unknown module type: {type(self)}")

    def get_extra_run_args(self) -> str:
        return (
            " ".join([f"--{arg[0]} {arg[1]}" for arg in self.extra_run_args])
            if self.extra_run_args
            else ""
        )


def _deploy_backend_to_pi(
    pi: _RaspberryPi,
    backend_local_path: str = "src/backend/",
):
    base_path = os.path.normpath(backend_local_path)

    if not base_path.endswith("/"):
        base_path = base_path + "/"

    remote_target_dir = f"{BACKEND_DEPLOYMENT_PATH.rstrip('/')}"

    mkdir_cmd = [
        "sshpass",
        "-p",
        pi.password,
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-p",
        str(pi.ssh_port),
        f"ubuntu@{pi.address}",
        f"mkdir -p {remote_target_dir}",
    ]

    mkdir_proc = subprocess.run(mkdir_cmd)
    if mkdir_proc.returncode != 0:
        raise Exception(
            f"Failed to create remote directory {remote_target_dir} on {pi.address}: {mkdir_proc.returncode}"
        )

    target = f"ubuntu@{pi.address}:{remote_target_dir}"

    rsync_cmd = [
        "sshpass",
        "-p",
        pi.password,
        "rsync",
        "-av",
        "--progress",
        "--rsync-path=sudo rsync",
        "--include=libs/***",
        "--exclude-from=" + GITIGNORE_PATH,
        "-e",
        f"ssh -p {getattr(pi, 'port', 22)} -o StrictHostKeyChecking=no",
    ]

    if EXCLUDE_CPP_DIR:
        rsync_cmd.append("--exclude=cpp/***")

    rsync_cmd.extend([base_path, target])

    exit_code = subprocess.run(rsync_cmd)
    if exit_code.returncode != 0:
        raise Exception(
            f"Failed to deploy backend from {base_path} on {pi.address}: {exit_code.returncode}"
        )


def _deploy_binaries(pi: _RaspberryPi, local_binaries_path: str):
    """Deploy a locally-built Rust binary to the Pi."""
    # Determine remote path
    remote_full_path = f"{BACKEND_DEPLOYMENT_PATH.rstrip('/')}/../{local_binaries_path}"

    print(f"Deploying {local_binaries_path} to {pi.address}:{remote_full_path}...")

    rmrf_cmd = [
        "sshpass",
        "-p",
        pi.password,
        "ssh",
        "-p",
        str(pi.ssh_port),
        f"ubuntu@{pi.address}",
        f"sudo rm -rf {remote_full_path}",
    ]

    rmrf_proc = subprocess.run(rmrf_cmd)
    if rmrf_proc.returncode != 0:
        raise Exception(
            f"Failed to remove remote directory {remote_full_path} on {pi.address}: {rmrf_proc.returncode}"
        )

    # Create remote directory
    mkdir_cmd = [
        "sshpass",
        "-p",
        pi.password,
        "ssh",
        "-p",
        str(pi.ssh_port),
        f"ubuntu@{pi.address}",
        f"sudo mkdir -p {remote_full_path}",
    ]

    mkdir_proc = subprocess.run(mkdir_cmd)
    if mkdir_proc.returncode != 0:
        raise Exception(
            f"Failed to create remote directory {remote_full_path} on {pi.address}: {mkdir_proc.returncode}"
        )

    # Upload the binary
    rsync_cmd = [
        "sshpass",
        "-p",
        pi.password,
        "rsync",
        "-av",
        "--progress",
        "--rsync-path=sudo rsync",
        "-e",
        f"ssh -p {getattr(pi, 'port', 22)} -o StrictHostKeyChecking=no",
        local_binaries_path,
        f"ubuntu@{pi.address}:{remote_full_path}",
    ]

    rsync_proc = subprocess.run(rsync_cmd)
    if rsync_proc.returncode != 0:
        raise Exception(
            f"Failed to upload binary to {remote_full_path} on {pi.address}: {rsync_proc.returncode}"
        )

    print(f"✓ Deployed {local_binaries_path} successfully")


def _deploy_compilable(pi: _RaspberryPi, modules: list[_Module]):
    from backend.deployment.compilation.cpp.cpp import CPlusPlus
    from backend.deployment.compilation.rust.rust import Rust

    if SHOULD_REBUILD_BINARIES:
        for module in modules:
            if not isinstance(module, _CompilableModule):
                continue

            assert isinstance(module, _CompilableModule)

            for platform in module.build_for_platforms:
                if isinstance(module, ModuleTypes.RustModule):
                    Rust.compile(module.runnable_name, platform)
                if isinstance(module, ModuleTypes.CPPLibraryModule):
                    CPlusPlus.compile(
                        module.name,
                        platform,
                        module.compilation_config,
                        module.project_root_folder_path,
                    )
                if isinstance(module, ModuleTypes.CPPRunnableModule):
                    CPlusPlus.compile(
                        module.runnable_name,
                        platform,
                        module.compilation_config,
                        module.project_root_folder_path,
                    )

    _deploy_binaries(pi, LOCAL_BINARIES_PATH)


def _deploy_on_pi(
    pi: _RaspberryPi,
    modules: list[_Module],
    backend_local_path: str = "src/backend/",
):
    _deploy_backend_to_pi(pi, backend_local_path)
    _deploy_compilable(pi, modules)

    restart_cmd = [
        "sshpass",
        "-p",
        pi.password,
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-p",
        str(pi.ssh_port),
        f"ubuntu@{pi.address}",
        f"echo {pi.password} | sudo -S systemctl restart startup.service",
    ]

    exit_code = subprocess.run(restart_cmd)
    if exit_code.returncode != 0:
        raise Exception(
            f"Failed to restart backend on {pi.address}: {exit_code.returncode}"
        )

    # Set config and processes via HTTP API after deployment
    if pi.processes_to_run:
        print(f"Setting config and processes on {pi.address}: {pi.processes_to_run}")
        try:
            config_base64 = _get_config()
            if not pi.stop_all_set_config_and_start(
                config_base64, new_processes_to_run=pi.processes_to_run
            ):
                print(
                    f"Warning: Failed to set config/processes on {pi.address} via HTTP API. "
                    "Config and processes may need to be set manually."
                )
        except Exception as e:
            print(
                f"Warning: Failed to get config or set config/processes on {pi.address}: {e}"
            )


def _verify_self():
    import importlib

    deploy_module = importlib.import_module("backend.deploy")
    all_functions = deploy_module.__dict__
    if "get_modules" not in all_functions:
        raise Exception(
            "get_modules() not found in backend.deploy. Please add a function that returns a list[Module] named get_modules(). THIS IS A REQUIRED FUNCTION."
        )

    get_modules = all_functions["get_modules"]
    pi_name_to_process_types = all_functions.get("pi_name_to_process_types")
    modules = get_modules()
    if not isinstance(modules, list) or not all(
        isinstance(m, _Module) for m in modules
    ):
        raise Exception(
            f"get_modules() returned {type(modules)} with element types {[type(m) for m in modules] if isinstance(modules, list) else 'N/A'} instead of list[Module]"
        )
    if pi_name_to_process_types is None or not callable(pi_name_to_process_types):
        raise Exception(
            "pi_name_to_process_types() not found in backend.deploy. Please add a function named pi_name_to_process_types. "
            "It must return dict[str, list[_WeightedProcess]] and may optionally accept a list[str] of discovered Pi names."
        )

    # Validate the output shape using a small synthetic Pi list.
    sig = inspect.signature(pi_name_to_process_types)
    if len(sig.parameters) == 0:
        mapping = pi_name_to_process_types()
    else:
        mapping = pi_name_to_process_types(["pi1", "pi2"])

    if not isinstance(mapping, dict) or not all(
        isinstance(k, str)
        and isinstance(v, Sequence)
        and not isinstance(v, (str, bytes))
        and all(isinstance(i, _WeightedProcess) for i in v)
        for k, v in mapping.items()
    ):
        raise Exception(
            f"pi_name_to_process_types() returned {type(mapping)} with element types "
            f"{[type(k) for k in mapping.keys()] if isinstance(mapping, dict) else 'N/A'} "
            f"instead of dict[str, list[_WeightedProcess]]"
        )


class _WeightedProcess(Enum):
    """
    This is a base class for a weighted process. It is used to represent a process that has a weight.

    Example usage:

    class ProcessType(_WeightedProcess):
        POS_EXTRAPOLATOR = "position-extrapolator", 0.5
        APRIL_SERVER = "april-server", 1.0

    """

    def __init__(self, name: str, weight: float):
        self._name = name
        self._weight = weight

    def __str__(self) -> str:
        return self._name

    def get_name(self) -> str:
        return self._name

    def get_weight(self) -> float:
        return self._weight


class ModuleTypes:
    @dataclass
    class CPPLibraryModule(_CompilableModule):
        name: str
        compilation_config: CPPBuildConfig

    @dataclass
    class CPPRunnableModule(_CompilableModule, _RunnableModule):
        compilation_config: CPPBuildConfig
        runnable_name: str
        runnable_extra_path: str = ""

        # TODO: fix this
        def get_run_command(self) -> str:
            return f"{LOCAL_BINARIES_PATH}/{get_self_ldd_version()}/{get_self_architecture()}/{self.runnable_name}{self.runnable_extra_path}".strip()

    @dataclass
    class RustModule(_CompilableModule, _RunnableModule):
        runnable_name: str

        def get_run_command(self) -> str:
            extra_run_args = self.get_extra_run_args()
            return f"{LOCAL_BINARIES_PATH}/{get_self_ldd_version()}/{get_self_architecture()}/rust/{self.runnable_name}/{self.runnable_name} {extra_run_args}".strip()

    @dataclass
    class ProtobufModule(_CompilableModule):
        pass

    @dataclass
    class ThriftModule(_CompilableModule):
        pass

    @dataclass
    class PythonModule(_RunnableModule):
        local_main_file_path: str
        local_root_folder_path: str

        def get_run_command(self) -> str:
            extra_run_args = self.get_extra_run_args()
            return f"{VENV_PATH} -u backend/{self.local_root_folder_path}/{self.local_main_file_path} {extra_run_args}"


class DeploymentOptions:
    @staticmethod
    def with_discovery_timeout(timeout_seconds: float):
        global DISCOVERY_TIMEOUT
        DISCOVERY_TIMEOUT = (  # pyright: ignore[reportConstantRedefinition]
            timeout_seconds  # pyright: ignore[reportConstantRedefinition]
        )
        _pi_api.DISCOVERY_TIMEOUT = timeout_seconds

    @staticmethod
    def with_custom_backend_dir(backend_dir: str):
        global BACKEND_DEPLOYMENT_PATH
        BACKEND_DEPLOYMENT_PATH = (  # pyright: ignore[reportConstantRedefinition]
            backend_dir  # pyright: ignore[reportConstantRedefinition]
        )

    @staticmethod
    def with_exclusions_from_gitignore(gitignore_path: str):
        global GITIGNORE_PATH
        GITIGNORE_PATH = gitignore_path  # pyright: ignore[reportConstantRedefinition]

    @staticmethod
    def with_preset_pi_addresses(
        pi_addresses: list[_RaspberryPi],
        modules: list[_Module],
        backend_local_path: str = "src/backend/",
    ):
        _verify_self()
        for pi in pi_addresses:
            _deploy_on_pi(pi, modules, backend_local_path)

    @staticmethod
    def with_automatic_discovery(
        modules: list[_Module],
        pi_name_to_process_types: Callable[
            ..., Mapping[str, Sequence[_WeightedProcess]]
        ],
        backend_local_path: str = "src/backend/",
    ):
        if os.path.exists(LOCAL_BINARIES_PATH):
            shutil.rmtree(LOCAL_BINARIES_PATH)
        os.makedirs(LOCAL_BINARIES_PATH, exist_ok=True)

        raspberrypis = _RaspberryPi.discover_all()

        process_mapping = pi_name_to_process_types([p.address for p in raspberrypis])

        print(
            "Process assignment:",
            {k: [str(p) for p in v] for k, v in process_mapping.items()},
        )

        # Import here to avoid circular dependency
        from backend.deployment.process_type_util import normalize_pi_name

        for pi in raspberrypis:
            assigned_processes = process_mapping.get(
                normalize_pi_name(pi.address or pi.host), []
            )
            pi.processes_to_run = [str(p) for p in assigned_processes]

        DeploymentOptions.with_preset_pi_addresses(
            raspberrypis, modules, backend_local_path
        )
        print()
        print()
        print(f"Deployed on {len(raspberrypis)} Pis")
        print()

    @staticmethod
    def with_exclude_cpp_dir(exclude_cpp_dir: bool):
        global EXCLUDE_CPP_DIR
        EXCLUDE_CPP_DIR = exclude_cpp_dir  # pyright: ignore[reportConstantRedefinition]

    @staticmethod
    def without_rebuilding_binaries(value: bool = True):
        global SHOULD_REBUILD_BINARIES
        SHOULD_REBUILD_BINARIES = (  # pyright: ignore[reportConstantRedefinition]
            not value
        )  # pyright: ignore[reportConstantRedefinition]


_verify_self()

# if you really want to use shorter types. Not recommended.
CPPLibraryModule = ModuleTypes.CPPLibraryModule
PythonModule = ModuleTypes.PythonModule
RustModule = ModuleTypes.RustModule
ProtobufModule = ModuleTypes.ProtobufModule
ThriftModule = ModuleTypes.ThriftModule
