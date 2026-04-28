from __future__ import annotations

from pathlib import Path

import pytest

from __tests__.docker_test_utils import DockerTestRunner


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLED_REPO = "/opt/blitz/B.L.I.T.Z"
SERVICE_NAME = "blitz-service"


@pytest.fixture
def docker_runner() -> DockerTestRunner:
    runner = DockerTestRunner(REPO_ROOT)
    try:
        yield runner
    finally:
        runner.cleanup()


def test_bootstrap_scripts_and_watchdog_service_registration(
    docker_runner: DockerTestRunner,
):
    image_tag = docker_runner.build_image("docker/Dockerfile.dev.test", "blitz-bootstrap-test")
    container = docker_runner.start_container(image_tag, "bootstrap")

    docker_runner.exec(
        container,
        f"""
        set -euo pipefail
        cd {INSTALLED_REPO}
        bash scripts/bootstrap/install_dependencies.sh
        command -v git
        command -v make
        command -v gcc
        command -v python3
        command -v pip3
        command -v sshpass
        command -v rsync
        command -v unzip
        command -v protoc
        command -v thrift
        """,
    )

    docker_runner.exec(
        container,
        f"""
        set -euo pipefail
        cd {INSTALLED_REPO}
        rm -f /etc/default/blitz /etc/profile.d/blitz.sh
        BLITZ_PATH={INSTALLED_REPO} bash scripts/bootstrap/install_links.sh
        grep -qx 'BLITZ_PATH={INSTALLED_REPO}' /etc/default/blitz
        test "$(stat -c '%a' /etc/default/blitz)" = "644"
        test "$(stat -c '%a' /etc/profile.d/blitz.sh)" = "644"
        bash -lc '. /etc/profile.d/blitz.sh && test "$BLITZ_PATH" = "{INSTALLED_REPO}"'
        """,
    )

    docker_runner.exec(
        container,
        f"""
        set -euo pipefail
        cd {INSTALLED_REPO}
        id ubuntu >/dev/null 2>&1 || useradd -m -s /bin/bash ubuntu
        BLITZ_PATH={INSTALLED_REPO} \\
        SERVICE_NAME={SERVICE_NAME} \\
        SERVICE_UNIT_SOURCE={INSTALLED_REPO}/ops/systemd/watchdog.service \\
        SERVICE_UNIT_PATH=/etc/systemd/system/{SERVICE_NAME}.service \\
        bash scripts/bootstrap/install_service.sh
        test -f /etc/systemd/system/{SERVICE_NAME}.service
        test "$(stat -c '%a' /etc/systemd/system/{SERVICE_NAME}.service)" = "644"
        test -L /etc/systemd/system/multi-user.target.wants/{SERVICE_NAME}.service
        systemctl cat {SERVICE_NAME} | grep -F 'scripts/runtime/run_watchdog.sh'
        systemctl is-enabled {SERVICE_NAME}
        journalctl -u {SERVICE_NAME} --no-pager >/tmp/{SERVICE_NAME}.journal
        """,
    )
