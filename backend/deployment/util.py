import dataclasses
from dataclasses import dataclass
import subprocess
import time
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceStateChange


SERVICE = "_deploy._udp.local."
DISCOVERY_TIMEOUT = 2.0
BACKEND_DEPLOYMENT_PATH = "~/Documents/B.L.I.T.Z/backend"
GITIGNORE_PATH = ".gitignore"
VENV_PATH = ".venv/bin/python"
MODULES = []


@dataclass
class CommonModule:
    local_root_folder_path: str
    extra_run_args: list[tuple[str, str]]
    equivalent_run_definition: str

    def get_run_command(self) -> str:
        return ""

    def _get_folder_name(self) -> str:
        return self.local_root_folder_path.rstrip("/").lstrip("./")

    def get_extra_run_args(self) -> str:
        return (
            "".join([f"--{arg[0]} {arg[1]}" for arg in self.extra_run_args])
            if self.extra_run_args
            else ""
        )


@dataclass
class RustModule(CommonModule):
    runnable_name: str

    def get_run_command(self) -> str:
        extra_run_args = self.get_extra_run_args()
        return f"cargo run --bin {self.runnable_name} -- {extra_run_args}"


@dataclass
class PythonModule(CommonModule):
    local_main_file_path: str

    def get_run_command(self) -> str:
        extra_run_args = self.get_extra_run_args()

        return f"{VENV_PATH} -m backend/{self.local_root_folder_path}/{self.local_main_file_path} {extra_run_args}"


@dataclass
class RaspberryPi:
    address: str
    host: str = dataclasses.field(default="ubuntu")
    password: str = dataclasses.field(default="ubuntu")

    @classmethod
    def _from_zeroconf(cls, service: ServiceInfo):
        assert service.server is not None
        return cls(
            address=service.name,
            host=service.server,
        )

    @classmethod
    def discover_all(cls):
        raspberrypis: list[RaspberryPi] = []
        zc = Zeroconf()
        _ = ServiceBrowser(
            zc,
            SERVICE,
            handlers=[lambda service: raspberrypis.append(cls._from_zeroconf(service))],
        )
        time.sleep(DISCOVERY_TIMEOUT)
        zc.close()
        return raspberrypis


def with_discovery_timeout(timeout_seconds: float):
    global DISCOVERY_TIMEOUT
    DISCOVERY_TIMEOUT = timeout_seconds  # pyright: ignore[reportConstantRedefinition]


def with_custom_backend_dir(backend_dir: str):
    global BACKEND_DEPLOYMENT_PATH
    BACKEND_DEPLOYMENT_PATH = backend_dir  # pyright: ignore[reportConstantRedefinition]


def _deploy_on_pi(pi: RaspberryPi, backend_local_path: str = "src/backend/"):
    target = f"ubuntu@{pi.address}:{BACKEND_DEPLOYMENT_PATH}"
    rsync_cmd = [
        "sshpass",
        "-p",
        pi.password,
        "rsync",
        "-av",
        "--progress",
        "--exclude-from=" + GITIGNORE_PATH,
        "--delete",
        backend_local_path,
        target,
    ]

    exit_code = subprocess.run(rsync_cmd)
    if exit_code.returncode != 0:
        raise Exception(
            f"Failed to deploy {backend_local_path} on {pi.address}: {exit_code.returncode}"
        )


def with_exclusions_from_gitignore(gitignore_path: str):
    global GITIGNORE_PATH
    GITIGNORE_PATH = gitignore_path  # pyright: ignore[reportConstantRedefinition]


def with_preset_pi_addresses(
    pi_addresses: list[RaspberryPi],
    backend_local_path: str = "src/backend/",
):
    for pi in pi_addresses:
        _deploy_on_pi(pi, backend_local_path)


def with_automatic_discovery(backend_local_path: str = "src/backend/"):
    raspberrypis = RaspberryPi.discover_all()
    with_preset_pi_addresses(raspberrypis, backend_local_path)


def set_modules(modules: list[CommonModule] | CommonModule):
    global MODULES
    if isinstance(modules, CommonModule):
        modules = [modules]

    MODULES = modules  # pyright: ignore[reportConstantRedefinition]
