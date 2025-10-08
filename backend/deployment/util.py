import dataclasses
from dataclasses import dataclass
from typing import Protocol
import subprocess
import time
import os
from typing_extensions import override
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener, ServiceInfo


SERVICE = "_deploy._udp.local."
DISCOVERY_TIMEOUT = 2.0
BACKEND_DEPLOYMENT_PATH = "~/Documents/B.L.I.T.Z/backend"
GITIGNORE_PATH = ".gitignore"
VENV_PATH = ".venv/bin/python"


@dataclass
class Module:
    pass


@dataclass
class CompilableModule(Module):
    project_root_folder_path: str


@dataclass
class RunnableModule(Module):
    extra_run_args: list[tuple[str, str]]
    equivalent_run_definition: str

    def get_run_command(self) -> str:
        return ""

    def get_lang_folder_name(self) -> str:
        if isinstance(self, PythonModule):
            return "python"
        elif isinstance(self, RustModule):
            return "rust"
        elif isinstance(self, ProtobufModule):
            return "proto"
        else:
            raise ValueError(f"Unknown module type: {type(self)}")

    def get_extra_run_args(self) -> str:
        return (
            " ".join([f"--{arg[0]} {arg[1]}" for arg in self.extra_run_args])
            if self.extra_run_args
            else ""
        )


@dataclass
class RustModule(RunnableModule):
    runnable_name: str
    build_on_deploy: bool = False

    @override
    def get_run_command(self) -> str:
        extra_run_args = self.get_extra_run_args()
        return f"cargo run --bin {self.runnable_name} -- {extra_run_args}"


@dataclass
class ProtobufModule(CompilableModule):
    pass


@dataclass
class PythonModule(RunnableModule):
    local_main_file_path: str
    local_root_folder_path: str

    @override
    def get_run_command(self) -> str:
        extra_run_args = self.get_extra_run_args()
        return f"{VENV_PATH} -u backend/{self.local_root_folder_path}/{self.local_main_file_path} {extra_run_args}"


class ZeroconfService(Protocol):
    server: str | None


@dataclass
class RaspberryPi:
    address: str
    host: str = dataclasses.field(default="ubuntu")
    password: str = dataclasses.field(default="ubuntu")

    @classmethod
    def _from_zeroconf(cls, service: ServiceInfo):
        assert service.server is not None
        return cls(
            address=service.server.rstrip("."),
            host=service.server.rstrip("."),
        )

    @classmethod
    def discover_all(cls):
        raspberrypis: list[RaspberryPi] = []
        zc = Zeroconf()

        class _Listener(ServiceListener):
            def __init__(self, out: list[RaspberryPi]):
                self.out: list[RaspberryPi] = out

            @override
            def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                info = zc.get_service_info(type_, name)
                if info is None:
                    return
                try:
                    self.out.append(RaspberryPi._from_zeroconf(info))
                except Exception:
                    pass

            @override
            def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                return

            @override
            def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                return

        _ = ServiceBrowser(zc, SERVICE, listener=_Listener(raspberrypis))
        time.sleep(DISCOVERY_TIMEOUT)
        zc.close()
        return raspberrypis


def with_discovery_timeout(timeout_seconds: float):
    global DISCOVERY_TIMEOUT
    DISCOVERY_TIMEOUT = timeout_seconds  # pyright: ignore[reportConstantRedefinition]


def with_custom_backend_dir(backend_dir: str):
    global BACKEND_DEPLOYMENT_PATH
    BACKEND_DEPLOYMENT_PATH = backend_dir  # pyright: ignore[reportConstantRedefinition]


def _deploy_backend_to_pi(
    pi: RaspberryPi,
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
        "--exclude-from=" + GITIGNORE_PATH,
        "--delete",
        "--delete-excluded",
        "-e",
        "ssh -o StrictHostKeyChecking=no",
        base_path,
        target,
    ]

    exit_code = subprocess.run(rsync_cmd)
    if exit_code.returncode != 0:
        raise Exception(
            f"Failed to deploy backend from {base_path} on {pi.address}: {exit_code.returncode}"
        )


def _deploy_compilable(pi: RaspberryPi, modules: list[Module]):
    for module in modules:
        if not isinstance(module, CompilableModule):
            continue

        remote_target_dir = f"{BACKEND_DEPLOYMENT_PATH.rstrip('/')}"
        target = f"ubuntu@{pi.address}:{remote_target_dir}"

        rsync_cmd = [
            "sshpass",
            "-p",
            pi.password,
            "rsync",
            "-av",
            "--progress",
            "--exclude-from=" + GITIGNORE_PATH,
            "--delete",
            "--delete-excluded",
            "-e",
            "ssh -o StrictHostKeyChecking=no",
            module.project_root_folder_path,
            target,
        ]

        exit_code = subprocess.run(rsync_cmd)
        if exit_code.returncode != 0:
            raise Exception(
                f"Failed to check if module {module.project_root_folder_path} is deployed on {pi.address}: {exit_code.returncode}"
            )


def _deploy_on_pi(
    pi: RaspberryPi,
    modules: list[Module],
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
        f"ubuntu@{pi.address}",
        f"echo {pi.password} | sudo -S systemctl restart startup.service",
    ]

    exit_code = subprocess.run(restart_cmd)
    if exit_code.returncode != 0:
        raise Exception(
            f"Failed to restart backend on {pi.address}: {exit_code.returncode}"
        )


def with_exclusions_from_gitignore(gitignore_path: str):
    global GITIGNORE_PATH
    GITIGNORE_PATH = gitignore_path  # pyright: ignore[reportConstantRedefinition]


def with_preset_pi_addresses(
    pi_addresses: list[RaspberryPi],
    modules: list[Module],
    backend_local_path: str = "src/backend/",
):
    for pi in pi_addresses:
        _deploy_on_pi(pi, modules, backend_local_path)


def _verify_self():
    import importlib

    deploy_module = importlib.import_module("backend.deploy")
    all_functions = deploy_module.__dict__
    if "get_modules" not in all_functions:
        raise Exception(
            "get_modules() not found in backend.deploy. Please add a function that returns a list[Module] named get_modules(). THIS IS A REQUIRED FUNCTION."
        )

    get_modules = all_functions["get_modules"]
    modules = get_modules()
    if not isinstance(modules, list) or not all(isinstance(m, Module) for m in modules):
        raise Exception(
            f"get_modules() returned {type(modules)} with element types {[type(m) for m in modules] if isinstance(modules, list) else 'N/A'} instead of list[Module]"
        )


def with_automatic_discovery(
    modules: list[Module], backend_local_path: str = "src/backend/"
):
    raspberrypis = RaspberryPi.discover_all()
    with_preset_pi_addresses(raspberrypis, modules, backend_local_path)
    print()
    print()
    print(f"Deployed on {len(raspberrypis)} Pis")
    print()


_verify_self()
