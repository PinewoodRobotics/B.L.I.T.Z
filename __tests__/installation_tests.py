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


@pytest.mark.parametrize(
    ("dockerfile", "tag_prefix", "container_suffix"),
    [
        ("docker/Dockerfile.dev.test", "blitz-dev-test", "dev"),
        ("docker/Dockerfile.unit.test", "blitz-unit-test", "unit"),
    ],
)
def test_setup_and_wipe_scripts_in_docker_container(
    docker_runner: DockerTestRunner,
    dockerfile: str,
    tag_prefix: str,
    container_suffix: str,
):
    image_tag = docker_runner.build_image(dockerfile, tag_prefix)
    container = docker_runner.start_container(image_tag, container_suffix)

    docker_runner.exec(
        container,
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
        """,
    )

    docker_runner.put_file(
        container,
        REPO_ROOT / "scripts" / "wipe.sh",
        f"{INSTALLED_REPO}/scripts/wipe.sh",
    )

    docker_runner.exec(
        container,
        f"""
        set -euo pipefail
        set -a
        . /etc/default/blitz
        set +a
        SERVICE_NAME={SERVICE_NAME} bash "$BLITZ_PATH/scripts/wipe.sh"
        """,
    )

    docker_runner.exec(
        container,
        f"""
        set -euo pipefail
        test ! -e /etc/default/blitz
        test ! -e /etc/profile.d/blitz.sh
        test ! -e /etc/systemd/system/{SERVICE_NAME}.service
        test ! -e {INSTALLED_REPO}
        """,
    )
