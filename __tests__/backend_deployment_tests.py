from __future__ import annotations

import json
import platform
import zipfile
import ast
from pathlib import Path

import pytest

from backend.deployment.bundler import CodeBundler
from backend.deployment.compilation.util.systems import SystemId
from backend.deployment.module.supported import SupportedModules
from backend.deployment.network_api.system_api import System
from backend.deployment.network_api.zeroconf import (
    DiscoveredNetworkSystem,
    RuntimePlatformInfo,
)
from backend.deployment.processes import WeightedProcess
from backend.deployment.rsyncer import Rsyncer
from __tests__.deploy_script_tests import INSTALLED_REPO
from __tests__.docker_test_utils import DockerTestRunner


REPO_ROOT = Path(__file__).resolve().parents[1]
REMOTE_BUNDLE_PATH = "backend-test-bundles"


class DeploymentTestProcess(WeightedProcess):
    SAMPLE = "sample-deployment-process", 1.0


@pytest.fixture
def docker_runner() -> DockerTestRunner:
    runner = DockerTestRunner(REPO_ROOT)
    try:
        yield runner
    finally:
        runner.cleanup()


def make_discovered_system(
    docker_runner: DockerTestRunner,
    target,
    hostname: str,
) -> DiscoveredNetworkSystem:
    raw_info = docker_runner.exec(
        target,
        """
        python3 -c 'import json, platform, sys
os_release = {}
with open("/etc/os-release") as f:
    for line in f:
        if "=" in line:
            key, value = line.rstrip().split("=", 1)
            os_release[key] = value.strip(chr(34))
print(json.dumps({
    "machine_architecture": platform.machine(),
    "platform_description": platform.platform(),
    "python_major_version": sys.version_info.major,
    "python_minor_version": sys.version_info.minor,
    "os_distribution_id": os_release.get("ID"),
    "os_distribution_family": os_release.get("ID_LIKE"),
    "os_distribution_version_id": os_release.get("VERSION_ID"),
}))'
        """,
    ).output.strip()
    info = json.loads(raw_info)
    return DiscoveredNetworkSystem(
        hostname=hostname,
        system_name="test",
        watchdog_port=5000,
        autobahn_port=8080,
        blitz_path=INSTALLED_REPO,
        runtime_platform=RuntimePlatformInfo(**info),
    )


def build_sample_python_module(tmp_path: Path) -> SupportedModules.PythonModule:
    module_root = tmp_path / "sample_deployment_module"
    module_root.mkdir()
    (module_root / "__main__.py").write_text(
        "import six\n"
        "from pathlib import Path\n"
        "Path('/tmp/blitz-deployment-module-ran').write_text(six.__version__)\n",
    )
    (tmp_path / "requirements.txt").write_text("six==1.17.0\n")
    return SupportedModules.PythonModule(
        name="sample_deployment_module",
        extra_run_args=[],
        equivalent_run_definition=DeploymentTestProcess.SAMPLE,
        module_folder_path=str(module_root),
    )


def prepare_existing_repo_ssh_target(docker_runner: DockerTestRunner, target) -> None:
    docker_runner.exec(
        target,
        f"""
        set -euo pipefail
        apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server sudo
        id ubuntu >/dev/null 2>&1 || useradd -m -s /bin/bash ubuntu
        echo 'ubuntu:ubuntu' | chpasswd
        usermod -aG sudo ubuntu
        printf '%s\n' 'ubuntu ALL=(ALL) NOPASSWD:ALL' >/etc/sudoers.d/ubuntu
        chmod 0440 /etc/sudoers.d/ubuntu
        mkdir -p /run/sshd
        sed -i 's/^#\\?PasswordAuthentication .*/PasswordAuthentication yes/' /etc/ssh/sshd_config
        systemctl restart ssh || /usr/sbin/sshd
        printf '%s\n' 'BLITZ_PATH={INSTALLED_REPO}' >/etc/default/blitz
        chown -R ubuntu:ubuntu {INSTALLED_REPO}
        chmod -R a+rwX {INSTALLED_REPO}
        if [ ! -x {INSTALLED_REPO}/.venv/bin/python ]; then
            python3 -m venv {INSTALLED_REPO}/.venv
        fi
        """,
    )


def test_backend_deploy_py_is_valid_and_bundled(tmp_path: Path):
    deploy_py = REPO_ROOT / "backend" / "deploy.py"
    deploy_source = deploy_py.read_text()
    parsed = ast.parse(deploy_source)
    function_names = {
        node.name for node in parsed.body if isinstance(node, ast.FunctionDef)
    }
    assert {"get_modules", "pi_name_to_process_types"} <= function_names

    system_id = SystemId(
        c_lib_version="2.39",
        linux_distro=make_ubuntu_24_distro(),
        architecture=make_host_architecture(),
        python_version=make_host_python_version(),
    )
    archive_path = CodeBundler(
        modules=[],
        backend_local_path="backend",
        build_folder_path=str(tmp_path / "build"),
        output_folder_path=str(tmp_path / "output"),
        system_id=system_id,
    ).bundle()

    bundle_root = f"backend-bundle-{system_id.to_build_key()}"
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        bundled_deploy_source = archive.read(f"{bundle_root}/deploy.py").decode()

    assert f"{bundle_root}/deploy.py" in names
    assert bundled_deploy_source == deploy_source


def test_rsyncer_deploys_backend_bundle_and_installs_python_dependencies(
    docker_runner: DockerTestRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    image_tag = docker_runner.build_image("docker/Dockerfile.dev.test", "blitz-backend-deploy-test")
    target = docker_runner.start_container(
        image_tag,
        "backend-deploy-target",
        ports={"22/tcp": ("127.0.0.1", None)},
    )
    prepare_existing_repo_ssh_target(docker_runner, target)

    target.reload()
    ssh_port = int(target.attrs["NetworkSettings"]["Ports"]["22/tcp"][0]["HostPort"])
    discovered_system = make_discovered_system(docker_runner, target, "127.0.0.1")
    system_id = discovered_system.to_system_id()
    module = build_sample_python_module(tmp_path)
    monkeypatch.chdir(tmp_path)

    archive_path = CodeBundler(
        modules=[module],
        backend_local_path=str(REPO_ROOT / "backend"),
        build_folder_path=str(tmp_path / "build"),
        output_folder_path=str(tmp_path / "output"),
        system_id=system_id,
        bundle_dependencies=True,
    ).bundle()
    assert Path(archive_path).exists()

    system = System(general_info=discovered_system)
    system.user = "ubuntu"
    system.password = "ubuntu"
    system.ssh_port = ssh_port
    Rsyncer(
        modules=[module],
        local_bundler_output_path=str(tmp_path / "output"),
        backend_bundle_path=REMOTE_BUNDLE_PATH,
        systems={system},
        are_deps_bundled=True,
    ).deploy()

    bundle_name = f"backend-bundle-{system_id.to_build_key()}.zip"
    docker_runner.exec(
        target,
        f"""
        set -euo pipefail
        test -f {INSTALLED_REPO}/{REMOTE_BUNDLE_PATH}/{bundle_name}
        test -f {INSTALLED_REPO}/backend/deploy.py
        test -f {INSTALLED_REPO}/backend/python/sample_deployment_module/__main__.py
        test -d {INSTALLED_REPO}/backend/deps/python
        ls {INSTALLED_REPO}/backend/deps/python/six-1.17.0-*.whl
        {INSTALLED_REPO}/.venv/bin/python -c 'import six; assert six.__version__ == "1.17.0"'
        cd {INSTALLED_REPO}
        .venv/bin/python backend/python/sample_deployment_module/__main__.py
        test "$(cat /tmp/blitz-deployment-module-ran)" = "1.17.0"
        """,
    )


def make_ubuntu_24_distro():
    from backend.deployment.compilation.util.systems import LinuxDistro

    return LinuxDistro.UBUNTU_24


def make_host_architecture():
    from backend.deployment.compilation.util.systems import Architecture

    return Architecture.from_machine(platform.machine())


def make_host_python_version():
    from backend.deployment.compilation.util.systems import PythonVersion

    return PythonVersion(major=3, minor=12)
