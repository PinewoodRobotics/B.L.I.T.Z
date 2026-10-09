"""Exercise the deployment tasks as Gradle runs them in an installed project."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
GRADLE_SCRIPTS = REPO_ROOT / "backend" / "deployment" / "gradle"


@pytest.fixture(params=["groovy", "kotlin"])
def gradle_project(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    if shutil.which("gradle") is None:
        pytest.skip("Gradle is not installed")

    backend = tmp_path / "backend"
    scripts = backend / "deployment" / "gradle"
    scripts.mkdir(parents=True)
    for name in ("build.gradle", "build.gradle.kts"):
        shutil.copy2(GRADLE_SCRIPTS / name, scripts / name)

    (backend / "deploy.py").write_text(
        """import os
import sys

print("found 3 systems", flush=True)
print("Docker build progress", flush=True)
print("Deployed on 2 Pis", flush=True)
print("phase=" + " ".join(sys.argv[1:]), flush=True)
if os.environ.get("BLITZ_TEST_FAIL_DEPLOY") == "1":
    print("simulated deployment failure", file=sys.stderr, flush=True)
    sys.exit(7)
"""
    )

    project = tmp_path / "robot"
    project.mkdir()
    if request.param == "groovy":
        (project / "settings.gradle").write_text(
            "rootProject.name = 'robot'\n"
            "gradle.ext.backendPath = file('../backend').absolutePath\n"
        )
        (project / "build.gradle").write_text(
            'apply from: "${gradle.ext.backendPath}/deployment/gradle/build.gradle"\n'
        )
    else:
        (project / "settings.gradle.kts").write_text(
            'rootProject.name = "robot"\n'
            'gradle.extra["backendPath"] = file("../backend").absolutePath\n'
        )
        (project / "build.gradle.kts").write_text(
            'apply(from = "${gradle.extra["backendPath"]}/deployment/gradle/build.gradle.kts")\n'
        )
    return project


def run_gradle(project: Path, *args: str, fail_deploy: bool = False) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if fail_deploy:
        environment["BLITZ_TEST_FAIL_DEPLOY"] = "1"
    return subprocess.run(
        ["gradle", "--offline", "--no-daemon", "--console=plain", "--quiet", *args],
        cwd=project,
        env=environment,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )


def test_gradle_deploy_and_cache_tasks(gradle_project: Path) -> None:
    result = run_gradle(
        gradle_project, "deployBackend", "cacheBackend", "-PEXPECTED_NUM_OF_PIS=2"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Docker build progress" in result.stdout
    assert "phase=\n" in result.stdout
    assert "phase=cache" in result.stdout


def test_gradle_deploy_checks_actual_deployed_count(gradle_project: Path) -> None:
    result = run_gradle(gradle_project, "deployBackend", "-PEXPECTED_NUM_OF_PIS=3")
    assert result.returncode != 0
    assert "Expected number of Pis: 3" in result.stdout
    assert "Deployed number of Pis: 2" in result.stdout


def test_gradle_deploy_propagates_python_failure(gradle_project: Path) -> None:
    result = run_gradle(gradle_project, "deployBackend", fail_deploy=True)
    assert result.returncode != 0
    assert "simulated deployment failure" in result.stderr
    assert "deploy.py exited with status 7" in result.stderr
