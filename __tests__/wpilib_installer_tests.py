from __future__ import annotations

import ast
import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "ui" / "install_on_wpilib.sh"
UPDATER = REPO_ROOT / "scripts" / "ui" / "update_wpilib.sh"
LOCAL_BACKEND_SCRIPT = REPO_ROOT / "scripts" / "wpi-local" / "backend.sh"


def make_wpilib_project(root: Path, *, kotlin_dsl: bool = False) -> Path:
    project = root / "robot"
    java_dir = project / "src" / "main" / "java" / "frc" / "robot"
    java_dir.mkdir(parents=True)
    if kotlin_dsl:
        (project / "build.gradle.kts").write_text(
            "plugins {\n"
            "    java\n"
            "}\n",
        )
        (project / "settings.gradle.kts").write_text("rootProject.name = \"robot\"\n")
    else:
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
    use_local_source: bool = True,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update({"BLITZ_ASSUME_YES": "true"})
    if use_local_source:
        merged_env["BLITZ_SOURCE_DIR"] = str(REPO_ROOT)
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


def run_updater(
    cwd: Path,
    env: dict[str, str] | None = None,
    use_local_source: bool = True,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update({"BLITZ_ASSUME_YES": "true"})
    if use_local_source:
        merged_env["BLITZ_SOURCE_DIR"] = str(REPO_ROOT)
    if env:
        merged_env.update(env)

    return subprocess.run(
        ["bash", str(UPDATER)],
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
    assert not (project / "backend" / "__init__.py").exists()
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
    assert (project / "scripts" / "backend.sh").is_file()


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


def test_rerun_refreshes_deployment_and_preserves_deploy_py(tmp_path: Path):
    project = make_wpilib_project(tmp_path)

    first = run_installer(project)
    assert_success(first)

    deploy_py = project / "backend" / "deploy.py"
    deploy_py.write_text("# team customization\n")

    second = run_installer(project)
    assert_success(second)

    build_gradle = project / "build.gradle"
    assert build_gradle.read_text().count("// BEGIN BLITZ BACKEND") == 1
    assert deploy_py.read_text() == "# team customization\n"


def test_installs_groovy_gradle_backend_task_blocks(tmp_path: Path):
    project = make_wpilib_project(tmp_path)

    result = run_installer(project)

    assert_success(result)
    settings_gradle = (project / "settings.gradle").read_text()
    build_gradle = (project / "build.gradle").read_text()
    assert 'gradle.ext.backendPath = file("backend").absolutePath' in settings_gradle
    assert 'apply from: "${gradle.ext.backendPath}/deployment/gradle/build.gradle"' in build_gradle
    assert "B.L.I.T.Z backend integration." in build_gradle
    assert "https://docs.gradle.org/current/userguide/plugins.html#sec:script_plugins" in build_gradle
    assert settings_gradle.count("// BEGIN BLITZ BACKEND") == 1
    assert build_gradle.count("// BEGIN BLITZ BACKEND") == 1


def test_installs_kotlin_gradle_backend_task_blocks(tmp_path: Path):
    project = make_wpilib_project(tmp_path, kotlin_dsl=True)

    result = run_installer(project)

    assert_success(result)
    settings_gradle = (project / "settings.gradle.kts").read_text()
    build_gradle = (project / "build.gradle.kts").read_text()
    assert 'gradle.extra["backendPath"] = file("backend").absolutePath' in settings_gradle
    assert 'apply(from = "${gradle.extra["backendPath"]}/deployment/gradle/build.gradle.kts")' in build_gradle
    assert "B.L.I.T.Z backend integration." in build_gradle
    assert "https://docs.gradle.org/current/userguide/plugins.html#sec:script_plugins" in build_gradle
    assert (project / "backend" / "deployment" / "gradle" / "build.gradle").is_file()
    assert (project / "backend" / "deployment" / "gradle" / "build.gradle.kts").is_file()


def run_local_backend_script(
    script: Path,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    return subprocess.run(
        ["bash", str(script)],
        cwd=cwd,
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_local_backend_script_detects_project_from_root_and_scripts_dir(tmp_path: Path):
    project = make_wpilib_project(tmp_path)

    install = run_installer(project)
    assert_success(install)

    root_result = run_local_backend_script(project / "scripts" / "backend.sh", project)
    scripts_result = run_local_backend_script(project / "scripts" / "backend.sh", project / "scripts")

    assert_success(root_result)
    assert_success(scripts_result)
    assert f"WPILib project: {project}" in root_result.stdout
    assert "Backend folder: backend" in root_result.stdout
    assert f"WPILib project: {project}" in scripts_result.stdout
    assert "Deployment:     backend/deployment" in scripts_result.stdout


def test_local_backend_script_changes_backend_folder_and_gradle_blocks(tmp_path: Path):
    project = make_wpilib_project(tmp_path)

    install = run_installer(project)
    assert_success(install)

    result = run_local_backend_script(
        project / "scripts" / "backend.sh",
        project,
        {
            "BLITZ_BACKEND_ACTION": "set-backend-dir",
            "BLITZ_BACKEND_DIR_VALUE": "robotBackend",
        },
    )

    assert_success(result)
    assert not (project / "backend").exists()
    assert (project / "robotBackend" / "deployment" / ".build-version").is_file()
    assert (project / "robotBackend" / "deploy.py").is_file()
    assert 'gradle.ext.backendPath = file("robotBackend").absolutePath' in (
        project / "settings.gradle"
    ).read_text()
    assert (
        '.set_local_backend_path("robotBackend")'
        in (project / "robotBackend" / "deploy.py").read_text()
    )
    assert (project / "settings.gradle").read_text().count("// BEGIN BLITZ BACKEND") == 1
    assert (project / "build.gradle").read_text().count("// BEGIN BLITZ BACKEND") == 1


def test_local_backend_script_creates_python_module_and_requirements(tmp_path: Path):
    project = make_wpilib_project(tmp_path)

    install = run_installer(project)
    assert_success(install)

    result = run_local_backend_script(
        project / "scripts" / "backend.sh",
        project,
        {
            "BLITZ_BACKEND_ACTION": "create-module",
            "BLITZ_MODULE_LANGUAGE": "python",
            "BLITZ_MODULE_NAME": "vision",
        },
    )

    assert_success(result)
    assert (project / "backend" / "python" / "vision" / "__main__.py").is_file()
    assert (project / "requirements.txt").is_file()


def test_local_backend_script_creates_rust_module_and_root_cargo(tmp_path: Path):
    project = make_wpilib_project(tmp_path)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    docker = fake_bin / "docker"
    docker.write_text("#!/bin/sh\nexit 0\n")
    docker.chmod(0o755)

    install = run_installer(project)
    assert_success(install)

    result = run_local_backend_script(
        project / "scripts" / "backend.sh",
        project,
        {
            "BLITZ_BACKEND_ACTION": "create-module",
            "BLITZ_MODULE_LANGUAGE": "rust",
            "BLITZ_MODULE_NAME": "pose",
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )

    assert_success(result)
    assert (project / "backend" / "rust" / "pose" / "src" / "main.rs").is_file()
    module_cargo = (project / "backend" / "rust" / "pose" / "Cargo.toml").read_text()
    assert 'name = "pose"' in module_cargo
    cargo = (project / "Cargo.toml").read_text()
    assert "[workspace]" in cargo
    assert 'members = ["backend/rust/*"]' in cargo
    assert "[workspace.dependencies]" in cargo
    assert 'rust-project = { path = "backend/rust" }' in cargo
    assert "[[bin]]" not in cargo


def test_local_backend_script_cpp_requires_docker(tmp_path: Path):
    project = make_wpilib_project(tmp_path)
    empty_path = tmp_path / "empty-path"
    empty_path.mkdir()

    install = run_installer(project)
    assert_success(install)

    result = run_local_backend_script(
        project / "scripts" / "backend.sh",
        project,
        {
            "BLITZ_BACKEND_ACTION": "create-module",
            "BLITZ_MODULE_LANGUAGE": "cpp",
            "BLITZ_MODULE_NAME": "native",
            "PATH": f"{empty_path}:/bin:/usr/bin",
        },
    )

    assert result.returncode != 0
    assert "Install Docker" in result.stderr
    assert not (project / "backend" / "cpp" / "native").exists()


def test_local_backend_script_creates_cpp_module_with_docker(tmp_path: Path):
    project = make_wpilib_project(tmp_path)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    docker = fake_bin / "docker"
    docker.write_text("#!/bin/sh\nexit 0\n")
    docker.chmod(0o755)

    install = run_installer(project)
    assert_success(install)

    result = run_local_backend_script(
        project / "scripts" / "backend.sh",
        project,
        {
            "BLITZ_BACKEND_ACTION": "create-module",
            "BLITZ_MODULE_LANGUAGE": "cpp",
            "BLITZ_MODULE_NAME": "native",
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )

    assert_success(result)
    assert (project / "backend" / "cpp" / "native" / "CMakeLists.txt").is_file()
    assert (project / "backend" / "cpp" / "native" / "src" / "main.cpp").is_file()


def test_update_only_requires_existing_install(tmp_path: Path):
    project = make_wpilib_project(tmp_path)

    result = run_installer(project, {"BLITZ_UPDATE_ONLY": "true"})

    assert result.returncode != 0
    assert "Update only was selected" in result.stderr


def test_updater_requires_existing_install(tmp_path: Path):
    project = make_wpilib_project(tmp_path)

    result = run_updater(project)

    assert result.returncode != 0
    assert "Could not find an installed BLITZ deployment folder" in result.stderr


def test_updater_reports_already_current(tmp_path: Path):
    project = make_wpilib_project(tmp_path)

    install = run_installer(project)
    assert_success(install)

    result = run_updater(project)

    assert_success(result)
    assert "already up to date" in result.stdout


def test_updater_accepts_kotlin_gradle_wpilib_project(tmp_path: Path):
    project = make_wpilib_project(tmp_path, kotlin_dsl=True)

    install = run_installer(project)
    assert_success(install)

    result = run_updater(project)

    assert_success(result)
    assert "already up to date" in result.stdout


def test_updater_refreshes_deployment_and_preserves_deploy_py(tmp_path: Path):
    project = make_wpilib_project(tmp_path)
    source = tmp_path / "source"

    install = run_installer(project)
    assert_success(install)

    deploy_py = project / "backend" / "deploy.py"
    deploy_py.write_text("# team customization\n")

    shutil.copytree(REPO_ROOT / "backend" / "deployment", source / "backend" / "deployment")
    (source / "backend" / "deployment" / ".build-version").write_text("9.9.9\n")
    extra_file = source / "backend" / "deployment" / "new_file.py"
    extra_file.write_text("UPDATED = True\n")
    local_script = source / "scripts" / "wpi-local" / "backend.sh"
    local_script.parent.mkdir(parents=True)
    local_script.write_text("#!/bin/bash\nprintf 'updated local backend script\\n'\n")

    result = run_updater(
        project,
        {
            "BLITZ_SOURCE_DIR": str(source),
            "BLITZ_LATEST_COMMIT_MESSAGE": "test update commit",
        },
    )

    assert_success(result)
    assert (project / "backend" / "deployment" / ".build-version").read_text() == "9.9.9\n"
    assert (project / "backend" / "deployment" / "new_file.py").read_text() == "UPDATED = True\n"
    assert deploy_py.read_text() == "# team customization\n"
    assert (project / "scripts" / "backend.sh").read_text() == (
        "#!/bin/bash\nprintf 'updated local backend script\\n'\n"
    )


def test_updater_auto_detects_custom_backend_folder(tmp_path: Path):
    project = make_wpilib_project(tmp_path)
    source = tmp_path / "source"

    install = run_installer(project, {"BLITZ_BACKEND_DIR": "robotBackend"})
    assert_success(install)

    deploy_py = project / "robotBackend" / "deploy.py"
    deploy_py.write_text("# custom deploy\n")

    shutil.copytree(REPO_ROOT / "backend" / "deployment", source / "backend" / "deployment")
    (source / "backend" / "deployment" / ".build-version").write_text("9.9.9\n")

    result = run_updater(
        project,
        {
            "BLITZ_SOURCE_DIR": str(source),
            "BLITZ_LATEST_COMMIT_MESSAGE": "custom backend update",
        },
    )

    assert_success(result)
    assert (project / "robotBackend" / "deployment" / ".build-version").read_text() == "9.9.9\n"
    assert deploy_py.read_text() == "# custom deploy\n"
    assert "Detected deployment folder: robotBackend/deployment" in result.stdout


def test_updater_does_not_clone_before_confirmation(tmp_path: Path):
    project = make_wpilib_project(tmp_path)

    install = run_installer(project)
    assert_success(install)

    result = run_updater(
        project,
        {
            "BLITZ_ASSUME_YES": "false",
            "BLITZ_LATEST_BUILD_VERSION": "9.9.9",
            "BLITZ_LATEST_COMMIT_MESSAGE": "available update",
        },
    )

    assert result.returncode != 0
    assert "confirmation is required" in result.stderr
    assert not (project / "bin" / "B.L.I.T.Z").exists()


def test_installs_from_git_source_when_local_source_is_not_set(tmp_path: Path):
    project = make_wpilib_project(tmp_path)

    result = run_installer(
        project,
        {
            "GIT_URL": f"file://{REPO_ROOT}",
        },
        use_local_source=False,
    )

    assert_success(result)
    assert (project / "backend" / "deployment" / "deployer.py").is_file()
    assert not (project / "bin" / "B.L.I.T.Z").exists()


def test_install_preserves_existing_bin_contents(tmp_path: Path):
    project = make_wpilib_project(tmp_path)
    keep_file = project / "bin" / "keep.txt"
    keep_file.parent.mkdir()
    keep_file.write_text("keep\n")

    result = run_installer(
        project,
        {"GIT_URL": f"file://{REPO_ROOT}"},
        use_local_source=False,
    )

    assert_success(result)
    assert keep_file.read_text() == "keep\n"
    assert not (project / "bin" / "B.L.I.T.Z").exists()


def test_dropdown_down_arrow_selects_second_option():
    result = run_dropdown_menu(INSTALLER, "\x1b[B\n")

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.endswith("1")


def test_dropdown_application_cursor_down_arrow_selects_second_option():
    result = run_dropdown_menu(INSTALLER, "\x1bOB\n")

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.endswith("1")


def test_dropdown_up_arrow_wraps_to_last_option():
    result = run_dropdown_menu(INSTALLER, "\x1b[A\n")

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.endswith("2")


def test_dropdown_application_cursor_up_arrow_wraps_to_last_option():
    result = run_dropdown_menu(INSTALLER, "\x1bOA\n")

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.endswith("2")


def test_dropdown_enter_selects_current_option():
    result = run_dropdown_menu(INSTALLER, "\n")

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.endswith("0")


def test_dropdown_q_selects_last_option():
    result = run_dropdown_menu(INSTALLER, "q")

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.endswith("2")


def test_system_installer_dropdown_down_arrow_selects_second_option():
    result = run_dropdown_menu(
        REPO_ROOT / "scripts" / "ui" / "install_on_system.sh",
        "\x1b[B\n",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.endswith("1")


def run_dropdown_menu(script: Path, input_text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            "-lc",
            (
                "set -euo pipefail; "
                f"source {script}; "
                "select_menu 'Test menu' 'First' 'Second' 'Third'; "
                "printf '%s' \"${selected_menu_index}\""
            ),
        ],
        cwd=REPO_ROOT,
        env={**os.environ, "BLITZ_UI_SOURCE_ONLY": "true", "TERM": "xterm-256color"},
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
