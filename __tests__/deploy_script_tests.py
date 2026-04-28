from __future__ import annotations

from pathlib import Path

import pytest

from __tests__.docker_test_utils import DockerTestRunner


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLED_REPO = "/opt/blitz/B.L.I.T.Z"
SERVICE_NAME = "blitz-service"
TARGET_ALIAS = "blitz-target"


@pytest.fixture
def docker_runner() -> DockerTestRunner:
    runner = DockerTestRunner(REPO_ROOT)
    try:
        yield runner
    finally:
        runner.cleanup()


def prepare_ssh_target(docker_runner: DockerTestRunner, target):
    docker_runner.exec(
        target,
        """
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
        printf '%s\n' 'BLITZ_PATH=/opt/blitz/B.L.I.T.Z' >/etc/default/blitz
        rm -rf /opt/blitz/B.L.I.T.Z
        mkdir -p /opt/blitz
        chmod 0777 /opt/blitz
        """,
    )


def assert_installed_on_target(docker_runner: DockerTestRunner, target):
    docker_runner.exec(
        target,
        f"""
        set -euo pipefail
        test -f {INSTALLED_REPO}/Makefile
        test -x {INSTALLED_REPO}/.venv/bin/python
        grep -qx 'BLITZ_PATH={INSTALLED_REPO}' /etc/default/blitz
        test -f /etc/profile.d/blitz.sh
        test -f /etc/systemd/system/{SERVICE_NAME}.service
        test "$(cat {INSTALLED_REPO}/system_data/name.txt)" = "test"
        test -f {INSTALLED_REPO}/watchdog/generated/PiStatus_pb2.py
        test -f {INSTALLED_REPO}/watchdog/generated/PiStatus_pb2.pyi
        test -f {INSTALLED_REPO}/watchdog/generated/StateLogging_pb2.py
        test -f {INSTALLED_REPO}/watchdog/generated/StateLogging_pb2.pyi
        systemctl cat {SERVICE_NAME} | grep -F 'scripts/runtime/run_watchdog.sh'
        systemctl is-enabled {SERVICE_NAME}
        """,
    )


def assert_wiped_on_target(docker_runner: DockerTestRunner, target):
    docker_runner.exec(
        target,
        f"""
        set -euo pipefail
        test ! -e /etc/default/blitz
        test ! -e /etc/profile.d/blitz.sh
        test ! -e /etc/systemd/system/{SERVICE_NAME}.service
        test ! -e {INSTALLED_REPO}
        """,
    )


def deploy_env() -> str:
    return (
        f"UBUNTU_TARGET={TARGET_ALIAS} "
        "TARGET_USER=ubuntu "
        "SSH_PASS=ubuntu "
        "TARGET_PORT=22 "
        "TARGET_NAME=test "
        "TARGET_FOLDER=/opt/blitz/ "
        f"SERVICE_NAME={SERVICE_NAME}"
    )


def test_deploy_scripts_against_real_ssh_target(docker_runner: DockerTestRunner):
    image_tag = docker_runner.build_image("docker/Dockerfile.dev.test", "blitz-deploy-test")
    network = docker_runner.create_network("deploy")
    controller = docker_runner.start_container(image_tag, "deploy-controller", network=network)
    target = docker_runner.start_container(
        image_tag,
        "deploy-target",
        network=network,
        aliases=[TARGET_ALIAS],
    )

    prepare_ssh_target(docker_runner, target)

    docker_runner.exec(
        controller,
        f"""
        set -euo pipefail
        cd {INSTALLED_REPO}
        {deploy_env()} bash scripts/deploy/sync_target_install.sh
        """,
    )
    assert_installed_on_target(docker_runner, target)

    docker_runner.exec(
        controller,
        f"""
        set -euo pipefail
        cd {INSTALLED_REPO}
        {deploy_env()} bash scripts/deploy/restart_target.sh
        """,
    )
    docker_runner.exec(target, f"systemctl cat {SERVICE_NAME} | grep -F '{SERVICE_NAME}.service'")

    docker_runner.exec(
        controller,
        f"""
        set -euo pipefail
        cd {INSTALLED_REPO}
        {deploy_env()} bash scripts/deploy/wipe_target.sh
        """,
    )
    assert_wiped_on_target(docker_runner, target)

    docker_runner.exec(
        controller,
        f"""
        set -euo pipefail
        cd {INSTALLED_REPO}
        {deploy_env()} bash scripts/deploy/flash_target.sh
        """,
    )
    docker_runner.exec(target, "test -f /tmp/setup.sh")
    assert_installed_on_target(docker_runner, target)
