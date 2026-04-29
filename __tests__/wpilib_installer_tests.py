from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "ui" / "install_on_wpilib.sh"


def make_wpilib_project(root: Path) -> Path:
    project = root / "robot"
    java_dir = project / "src" / "main" / "java" / "frc" / "robot"
    java_dir.mkdir(parents=True)
    (project / "build.gradle").write_text(
        "plugins {\n"
        "    id 'java'\n"
        "}\n",
    )
    (project / "settings.gradle").write_text("rootProject.name = 'robot'\n")
    (java_dir / "Robot.java").write_text("package frc.robot;\n")
    return project


def run_installer(
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(
        {
            "BLITZ_ASSUME_YES": "true",
            "BLITZ_SOURCE_DIR": str(REPO_ROOT),
        }
    )
    if env:
        merged_env.update(env)

    return subprocess.run(
        ["bash", str(INSTALLER)],
        cwd=cwd,
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def assert_success(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


def test_installs_into_discovered_wpilib_project_from_nested_directory(tmp_path: Path):
    project = make_wpilib_project(tmp_path)
    nested = project / "src" / "main" / "java"

    result = run_installer(nested)

    assert_success(result)
    assert (project / "backend" / "deployment" / "deployer.py").is_file()
    assert (project / "backend" / "__init__.py").is_file()
    deploy_py = project / "backend" / "deploy.py"
    assert deploy_py.is_file()
    deploy_source = deploy_py.read_text()
    ast.parse(deploy_source)
    assert '.set_local_backend_path("backend")' in deploy_source

    import_result = subprocess.run(
        [
            "python",
            "-c",
            "import backend.deployment.processes as p; print(p.ProcessPlan.__name__)",
        ],
        cwd=project,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert import_result.returncode == 0, import_result.stdout + import_result.stderr
    assert import_result.stdout.strip() == "ProcessPlan"


def test_rejects_non_wpilib_directory(tmp_path: Path):
    result = run_installer(tmp_path)

    assert result.returncode != 0
    assert "WPILIB_PROJECT is required" in result.stderr


def test_rejects_explicit_non_wpilib_project(tmp_path: Path):
    project = tmp_path / "plain"
    project.mkdir()

    result = run_installer(tmp_path, {"WPILIB_PROJECT": str(project)})

    assert result.returncode != 0
    assert "does not look like a Java WPILib project" in result.stderr


def test_gradle_task_is_idempotent_and_deploy_py_is_preserved(tmp_path: Path):
    project = make_wpilib_project(tmp_path)

    first = run_installer(
        project,
        {
            "BLITZ_GRADLE_INTEGRATION": "true",
            "BLITZ_GRADLE_TASK": "deployBlitz",
        },
    )
    assert_success(first)

    deploy_py = project / "backend" / "deploy.py"
    deploy_py.write_text("# team customization\n")

    second = run_installer(
        project,
        {
            "BLITZ_GRADLE_INTEGRATION": "true",
            "BLITZ_GRADLE_TASK": "deployBlitz",
        },
    )
    assert_success(second)

    build_gradle = (project / "build.gradle").read_text()
    assert build_gradle.count("// BEGIN BLITZ DEPLOY TASK") == 1
    assert build_gradle.count("// END BLITZ DEPLOY TASK") == 1
    assert "tasks.register('deployBlitz', Exec)" in build_gradle
    assert "commandLine 'python3', 'backend/deploy.py'" in build_gradle
    assert deploy_py.read_text() == "# team customization\n"


def test_update_only_requires_existing_install(tmp_path: Path):
    project = make_wpilib_project(tmp_path)

    result = run_installer(project, {"BLITZ_UPDATE_ONLY": "true"})

    assert result.returncode != 0
    assert "Update only was selected" in result.stderr
