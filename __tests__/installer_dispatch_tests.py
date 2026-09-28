from __future__ import annotations

import os
import pty
import subprocess
from pathlib import Path

import pytest

from __tests__.wpilib_installer_tests import make_wpilib_project


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "ui" / "install.sh"


def run_installer(
    project: Path, settings: dict[str, str], *, piped: bool = False
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("BLITZ_INSTALL_TARGET", None)
    environment.pop("BLITZ_SOURCE_DIR", None)
    environment.update(settings)
    command = ["bash", "-c", INSTALLER.read_text()] if piped else ["bash", str(INSTALLER)]
    return subprocess.run(
        command,
        cwd=project,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def run_interactive_installer(
    project: Path, settings: dict[str, str], selection: str
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("BLITZ_INSTALL_TARGET", None)
    environment.update(settings)
    master, slave = pty.openpty()
    try:
        with subprocess.Popen(
            ["bash", str(INSTALLER)],
            cwd=project,
            env=environment,
            stdin=slave,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as process:
            os.close(slave)
            slave = -1
            os.write(master, f"{selection}\n".encode())
            stdout, stderr = process.communicate(timeout=10)
            return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
    finally:
        os.close(master)
        if slave != -1:
            os.close(slave)


def test_installer_dispatches_to_selected_component(tmp_path: Path) -> None:
    source = tmp_path / "source"
    scripts = source / "scripts" / "ui"
    scripts.mkdir(parents=True)
    for target, name in (
        ("coprocessor", "install_on_system.sh"),
        ("development", "install_backend.sh"),
    ):
        (scripts / name).write_text(f"#!/bin/bash\nprintf '%s\\n' {target}\n")
        result = run_installer(
            tmp_path,
            {"BLITZ_SOURCE_DIR": str(source), "BLITZ_INSTALL_TARGET": target},
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == target


def test_interactive_menu_selects_both_components(tmp_path: Path) -> None:
    scripts = tmp_path / "source" / "scripts" / "ui"
    scripts.mkdir(parents=True)
    (scripts / "install_backend.sh").write_text("#!/bin/bash\nprintf '%s\\n' selected-development\n")
    (scripts / "install_on_system.sh").write_text("#!/bin/bash\nprintf '%s\\n' selected-coprocessor\n")
    for selection, expected in (("1", "selected-coprocessor"), ("2", "selected-development")):
        result = run_interactive_installer(
            tmp_path, {"BLITZ_SOURCE_DIR": str(tmp_path / "source")}, selection
        )
        assert result.returncode == 0, result.stderr
        assert "1) Coprocessor" in result.stdout
        assert "2) Development computer" in result.stdout
        assert expected in result.stdout


def test_interactive_menu_cancel_and_invalid_choice(tmp_path: Path) -> None:
    for selection, code, message in (
        ("3", 0, "Installation cancelled."),
        ("4", 1, "Invalid selection: 4"),
    ):
        result = run_interactive_installer(tmp_path, {}, selection)
        assert result.returncode == code
        assert message in result.stdout + result.stderr


@pytest.mark.parametrize(
    ("target", "url_setting"),
    [
        ("coprocessor", "BLITZ_SYSTEM_INSTALLER_URL"),
        ("development", "BLITZ_BACKEND_INSTALLER_URL"),
    ],
)
def test_piped_installer_fetches_selected_component(
    tmp_path: Path, target: str, url_setting: str
) -> None:
    remote = tmp_path / "remote-installer.sh"
    remote.write_text(f"#!/bin/bash\nprintf '%s\\n' fetched-{target}\n")
    result = run_installer(
        tmp_path,
        {
            "BLITZ_INSTALL_TARGET": target,
            url_setting: remote.as_uri(),
        },
        piped=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"fetched-{target}"


def test_installer_requires_valid_choice_without_terminal(tmp_path: Path) -> None:
    missing = run_installer(tmp_path, {})
    assert missing.returncode != 0
    assert "BLITZ_INSTALL_TARGET" in missing.stderr

    invalid = run_installer(tmp_path, {"BLITZ_INSTALL_TARGET": "unknown"})
    assert invalid.returncode != 0
    assert "Unknown BLITZ_INSTALL_TARGET" in invalid.stderr


def test_unified_installer_sets_up_plain_development_project(tmp_path: Path) -> None:
    project = tmp_path / "plain-app"
    project.mkdir()
    result = run_installer(
        project,
        {
            "BLITZ_SOURCE_DIR": str(REPO_ROOT),
            "BLITZ_INSTALL_TARGET": "development",
            "BLITZ_SETUP": "none",
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / "backend" / "deployment" / ".blitz-build-version").is_file()
    assert (project / "scripts" / "backend.sh").is_file()
    assert not (project / "build.gradle").exists()


def test_interactive_choice_installs_development_backend(tmp_path: Path) -> None:
    project = tmp_path / "plain-app"
    project.mkdir()
    result = run_interactive_installer(
        project,
        {
            "BLITZ_SOURCE_DIR": str(REPO_ROOT),
            "BLITZ_SETUP": "none",
            "BLITZ_ASSUME_YES": "true",
        },
        "2",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / "backend" / "deployment" / ".blitz-build-version").is_file()
    assert not (project / "build.gradle").exists()


def test_piped_unified_installer_sets_up_wpilib_project(tmp_path: Path) -> None:
    project = make_wpilib_project(tmp_path)
    result = run_installer(
        project,
        {
            "BLITZ_INSTALL_TARGET": "development",
            "BLITZ_BACKEND_INSTALLER_URL": (REPO_ROOT / "scripts" / "ui" / "install_backend.sh").as_uri(),
            "BLITZ_SOURCE_DIR": str(REPO_ROOT),
            "BLITZ_SETUP": "wpilib",
            "BLITZ_ASSUME_YES": "true",
        },
        piped=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / "backend" / "deployment" / ".blitz-build-version").is_file()
    assert "BEGIN BLITZ BACKEND" in (project / "build.gradle").read_text()


def test_unified_installer_runs_coprocessor_setup(tmp_path: Path) -> None:
    setup_script = tmp_path / "setup.sh"
    setup_script.write_text(
        "#!/bin/bash\n"
        "printf '%s\\n' \"${TARGET_NAME}|${TARGET_FOLDER}|${SERVICE_NAME}\" >\"${SETUP_RESULT}\"\n"
    )
    commands = tmp_path / "commands"
    commands.mkdir()
    for name, body in (
        ("uname", "#!/bin/bash\ncase \"$1\" in -s) echo Linux ;; -r) echo 6.1.0 ;; esac\n"),
        ("sudo", "#!/bin/bash\nexit 0\n"),
    ):
        command = commands / name
        command.write_text(body)
        command.chmod(0o755)
    result_path = tmp_path / "setup-result.txt"
    result = run_installer(
        tmp_path,
        {
            "BLITZ_INSTALL_TARGET": "coprocessor",
            "BLITZ_SOURCE_DIR": str(REPO_ROOT),
            "BLITZ_ASSUME_YES": "true",
            "BLITZ_SETUP_SCRIPT": str(setup_script),
            "SETUP_RESULT": str(result_path),
            "TARGET_NAME": "robot-coprocessor",
            "TARGET_FOLDER": "/opt/blitz-test",
            "SERVICE_NAME": "blitz-test",
            "PATH": f"{commands}:{os.environ['PATH']}",
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result_path.read_text() == "robot-coprocessor|/opt/blitz-test|blitz-test\n"
    assert "BLITZ installation complete." in result.stdout
