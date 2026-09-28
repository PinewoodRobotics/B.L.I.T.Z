from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

from __tests__.wpilib_installer_tests import make_wpilib_project


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "ui" / "install_backend.sh"
UPDATER = REPO_ROOT / "scripts" / "ui" / "update_backend.sh"


def run_script(script: Path, project: Path, settings: dict[str, str]) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update({"BLITZ_PROJECT": str(project), "BLITZ_SOURCE_DIR": str(REPO_ROOT)})
    environment.update(settings)
    return subprocess.run(
        ["bash", str(script)],
        cwd=project,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def assert_success(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


def test_plain_project_installs_backend_without_gradle_and_deploys(tmp_path: Path) -> None:
    project = tmp_path / "plain-app"
    project.mkdir()
    assert_success(run_script(INSTALLER, project, {"BLITZ_SETUP": "none"}))

    deployment = project / "backend" / "deployment"
    assert (deployment / ".blitz-build-version").is_file()
    assert (deployment / "deployer.py").is_file()
    assert not (project / "build.gradle").exists()
    assert not (project / "settings.gradle").exists()
    deploy_script = project / "backend" / "deploy.py"
    function_names = {
        node.name
        for node in ast.parse(deploy_script.read_text()).body
        if isinstance(node, ast.FunctionDef)
    }
    assert {"get_modules", "pi_name_to_process_types"} <= function_names
    imported = subprocess.run(
        [
            sys.executable,
            "-c",
            "from backend.deploy import get_modules, pi_name_to_process_types; "
            "assert get_modules() == []; assert pi_name_to_process_types([]) == {}",
        ],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )
    assert_success(imported)

    local_script = project / "scripts" / "backend.sh"
    status = run_script(local_script, project, {"BLITZ_BACKEND_ACTION": "status"})
    assert_success(status)
    assert "Backend folder: backend" in status.stdout
    discovery_env = os.environ.copy()
    discovery_env.pop("BLITZ_PROJECT", None)
    discovery_env["BLITZ_BACKEND_ACTION"] = "status"
    discovered = subprocess.run(
        ["bash", str(local_script)],
        cwd=project / "scripts",
        env=discovery_env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert_success(discovered)
    assert f"Project:        {project}" in discovered.stdout

    deploy_script.write_text(
        "from backend.deployment.processes import ProcessPlan\n"
        "from pathlib import Path\n"
        "Path('deployed.txt').write_text(ProcessPlan.__name__)\n"
    )
    deployed = run_script(local_script, project, {"BLITZ_BACKEND_ACTION": "deploy"})
    assert_success(deployed)
    assert (project / "deployed.txt").read_text() == "ProcessPlan"

    assert_success(run_script(INSTALLER, project, {"BLITZ_SETUP": "none"}))
    assert deploy_script.read_text().startswith("from backend.deployment.processes")


def test_stamp_locates_custom_backend_in_plain_project(tmp_path: Path) -> None:
    project = tmp_path / "plain-app"
    project.mkdir()
    assert_success(
        run_script(
            INSTALLER,
            project,
            {"BLITZ_SETUP": "none", "BLITZ_BACKEND_DIR": "services/robotBackend"},
        )
    )
    assert (project / "services" / "robotBackend" / "deployment" / ".blitz-build-version").is_file()
    assert (project / "backend").is_symlink()

    local_script = project / "scripts" / "backend.sh"
    status = run_script(local_script, project, {"BLITZ_BACKEND_ACTION": "status"})
    assert_success(status)
    assert "Backend folder: services/robotBackend" in status.stdout

    updated = run_script(UPDATER, project, {"BLITZ_LATEST_COMMIT_MESSAGE": "local version"})
    assert_success(updated)
    assert "already up to date" in updated.stdout

    moved_backend = project / "tools" / "runtime"
    moved_backend.parent.mkdir()
    (project / "services" / "robotBackend").rename(moved_backend)
    (project / "backend").unlink()
    (moved_backend / "deploy.py").write_text(
        "from backend.deployment.processes import ProcessPlan\n"
        "from pathlib import Path\n"
        "Path('moved-deploy.txt').write_text(ProcessPlan.__name__)\n"
    )
    moved_status = run_script(local_script, project, {"BLITZ_BACKEND_ACTION": "status"})
    assert_success(moved_status)
    assert "Backend folder: tools/runtime" in moved_status.stdout
    assert_success(run_script(local_script, project, {"BLITZ_BACKEND_ACTION": "deploy"}))
    assert (project / "moved-deploy.txt").read_text() == "ProcessPlan"


def test_plain_project_update_follows_stamp_and_preserves_deploy_script(tmp_path: Path) -> None:
    project = tmp_path / "plain-app"
    project.mkdir()
    assert_success(run_script(INSTALLER, project, {"BLITZ_SETUP": "none"}))
    deploy_script = project / "backend" / "deploy.py"
    deploy_script.write_text("# team customization\n")

    source = tmp_path / "new-source"
    shutil.copytree(
        REPO_ROOT / "backend" / "deployment", source / "backend" / "deployment"
    )
    (source / "backend" / "deployment" / ".blitz-build-version").write_text("9.9.9\n")
    (source / "backend" / "deployment" / "new_file.py").write_text("UPDATED = True\n")
    local_script = source / "scripts" / "wpi-local" / "backend.sh"
    local_script.parent.mkdir(parents=True)
    shutil.copy2(REPO_ROOT / "scripts" / "wpi-local" / "backend.sh", local_script)

    result = run_script(
        UPDATER,
        project,
        {
            "BLITZ_SOURCE_DIR": str(source),
            "BLITZ_ASSUME_YES": "true",
            "BLITZ_UI_LIB_URL": f"file://{REPO_ROOT / 'scripts' / 'ui' / 'common' / 'terminal_ui.sh'}",
            "BLITZ_LATEST_COMMIT_MESSAGE": "new build",
        },
    )
    assert_success(result)
    assert "updated to 9.9.9" in result.stdout
    assert (project / "backend" / "deployment" / ".blitz-build-version").read_text() == "9.9.9\n"
    assert (project / "backend" / "deployment" / "new_file.py").read_text() == "UPDATED = True\n"
    assert deploy_script.read_text() == "# team customization\n"


def test_wpilib_setup_is_explicit_option(tmp_path: Path) -> None:
    project = make_wpilib_project(tmp_path)
    assert_success(run_script(INSTALLER, project, {"BLITZ_SETUP": "none"}))
    assert "BEGIN BLITZ BACKEND" not in (project / "build.gradle").read_text()

    local_script = project / "scripts" / "backend.sh"
    assert_success(run_script(local_script, project, {"BLITZ_BACKEND_ACTION": "setup-wpilib"}))
    assert "BEGIN BLITZ BACKEND" in (project / "build.gradle").read_text()
    assert "BEGIN BLITZ BACKEND" in (project / "settings.gradle").read_text()


def test_wpilib_install_option_keeps_gradle_integration(tmp_path: Path) -> None:
    project = make_wpilib_project(tmp_path)
    assert_success(run_script(INSTALLER, project, {"BLITZ_SETUP": "wpilib"}))
    assert (project / "backend" / "deployment" / ".blitz-build-version").is_file()
    assert "BEGIN BLITZ BACKEND" in (project / "build.gradle").read_text()


def test_setup_wpilib_rejects_plain_project(tmp_path: Path) -> None:
    project = tmp_path / "plain-app"
    project.mkdir()
    assert_success(run_script(INSTALLER, project, {"BLITZ_SETUP": "none"}))

    result = run_script(
        project / "scripts" / "backend.sh",
        project,
        {"BLITZ_BACKEND_ACTION": "setup-wpilib"},
    )
    assert result.returncode != 0
    assert "requires a Java WPILib project" in result.stderr


def test_plain_project_can_move_backend_without_gradle(tmp_path: Path) -> None:
    project = tmp_path / "plain-app"
    project.mkdir()
    assert_success(run_script(INSTALLER, project, {"BLITZ_SETUP": "none"}))

    moved = run_script(
        project / "scripts" / "backend.sh",
        project,
        {
            "BLITZ_BACKEND_ACTION": "set-backend-dir",
            "BLITZ_BACKEND_DIR_VALUE": "robotBackend",
        },
    )
    assert_success(moved)
    assert (project / "robotBackend" / "deployment" / ".blitz-build-version").is_file()
    assert (project / "backend").is_symlink()
    assert not (project / "build.gradle").exists()


def test_multiple_backend_stamps_are_rejected(tmp_path: Path) -> None:
    project = tmp_path / "plain-app"
    project.mkdir()
    assert_success(run_script(INSTALLER, project, {"BLITZ_SETUP": "none"}))
    second_deployment = project / "another" / "deployment"
    second_deployment.mkdir(parents=True)
    (second_deployment / ".blitz-build-version").write_text("1.0.0\n")

    status = run_script(
        project / "scripts" / "backend.sh",
        project,
        {"BLITZ_BACKEND_ACTION": "status"},
    )
    assert status.returncode != 0
    assert "multiple BLITZ backend stamps" in status.stderr
