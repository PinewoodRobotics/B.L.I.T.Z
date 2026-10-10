from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from __tests__.docker_resources import DockerTestResources
from __tests__.docker_test_utils import DockerTestRunner
from backend.deployment.compilation import system_builder


@pytest.fixture(scope="session")
def docker_test_resources() -> Iterator[DockerTestResources]:
    resources = DockerTestResources()
    try:
        yield resources
    finally:
        resources.cleanup()


@pytest.fixture(scope="module")
def docker_builds(docker_test_resources: DockerTestResources) -> Iterator[DockerTestResources]:
    # Mock-based unit tests keep the ordinary commands. Only actual Docker tests
    # select this fixture and route builds through the isolated session builder.
    dependency_image = system_builder.SystemBuilder.dependency_image

    def isolated_dependency_image(builder: system_builder.SystemBuilder) -> str:
        return docker_test_resources.image_name(dependency_image(builder))

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(system_builder, "run_command", docker_test_resources.run)
        patch.setattr(
            system_builder.SystemBuilder, "dependency_image",
            isolated_dependency_image,
        )
        yield docker_test_resources


@pytest.fixture
def docker_runner(docker_builds: DockerTestResources) -> Iterator[DockerTestRunner]:
    runner = DockerTestRunner(Path(__file__).resolve().parents[1], docker_builds)
    try:
        yield runner
    finally:
        runner.cleanup()
