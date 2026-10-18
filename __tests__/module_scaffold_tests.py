from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from __tests__.backend_installer_tests import INSTALLER, REPO_ROOT, assert_success, run_script
from backend.deployment.module.scaffold import ModuleLanguage, register_module, scaffold_module


INSTALLER_STYLE_DEPLOY = '''from backend.deployment.module.supported import SupportedModules
from backend.deployment.processes import ProcessPlan, WeightedProcess


class ProcessType(WeightedProcess):
    pass


def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return ProcessPlan[ProcessType]().assign(pi_names)


def get_modules() -> list[SupportedModules._Generic]:
    return []
'''

POPULATED_DEPLOY = '''from backend.deployment.module.catalog import BackendModules
from backend.deployment.module.supported import SupportedModules
from backend.deployment.processes import ProcessPlan, WeightedProcess

modules = BackendModules(__file__)


class ProcessType(WeightedProcess):
    CONTROL = "control-process", 1.0


def get_modules() -> list[SupportedModules._Generic]:
    return [
        modules.python("control", process=ProcessType.CONTROL, entrypoint="main.py"),
    ]


def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return (
        ProcessPlan[ProcessType]()
        .add(ProcessType.CONTROL)
        .assign(pi_names)
    )
'''


def load_deploy(backend: Path):
    namespace: dict = {"__file__": str(backend / "deploy.py")}
    exec(compile((backend / "deploy.py").read_text(), str(backend / "deploy.py"), "exec"), namespace)
    return namespace


def test_registers_module_in_empty_installer_template() -> None:
    updated = register_module(INSTALLER_STYLE_DEPLOY, "vision", ModuleLanguage.CPP)
    assert updated is not None
    assert "from backend.deployment.module.catalog import BackendModules" in updated
    assert "modules = BackendModules(__file__)" in updated
    assert 'VISION = "vision", 1.0' in updated
    assert "pass" not in updated
    assert 'modules.cpp("vision", process=ProcessType.VISION),' in updated
    assert (
        "    return (\n"
        "        ProcessPlan[ProcessType]()\n"
        "        .add(ProcessType.VISION)\n"
        "        .assign(pi_names)\n"
        "    )\n"
    ) in updated


def test_registers_module_alongside_existing_modules() -> None:
    updated = register_module(POPULATED_DEPLOY, "drive-base", ModuleLanguage.RUST)
    assert updated is not None
    assert updated.count("modules = BackendModules(__file__)") == 1
    assert '    CONTROL = "control-process", 1.0\n    DRIVE_BASE = "drive-base", 1.0\n' in updated
    assert (
        '        modules.python("control", process=ProcessType.CONTROL, entrypoint="main.py"),\n'
        '        modules.rust("drive-base", process=ProcessType.DRIVE_BASE),\n'
        '    ]'
    ) in updated
    assert "        .add(ProcessType.CONTROL)\n        .add(ProcessType.DRIVE_BASE)\n        .assign(pi_names)" in updated


def test_unrecognized_deploy_layout_is_left_untouched(tmp_path: Path) -> None:
    deploy = tmp_path / "deploy.py"
    original = "def get_modules():\n    return build_modules()\n"
    deploy.write_text(original)
    result = scaffold_module(tmp_path, "telemetry", ModuleLanguage.PYTHON)
    assert not result.registered
    assert deploy.read_text() == original
    assert 'modules.python("telemetry", process=ProcessType.TELEMETRY)' in result.manual_steps
    assert (tmp_path / "python" / "telemetry" / "__main__.py").is_file()


@pytest.mark.parametrize("name", ["common", "1abc", "bad name", "../escape", ""])
def test_rejects_invalid_module_names(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError):
        scaffold_module(tmp_path, name, ModuleLanguage.PYTHON)


def test_rejects_existing_folder_and_process(tmp_path: Path) -> None:
    (tmp_path / "deploy.py").write_text(POPULATED_DEPLOY)
    with pytest.raises(ValueError, match="already exists"):
        scaffold_module(tmp_path, "control", ModuleLanguage.CPP)
    (tmp_path / "rust" / "taken").mkdir(parents=True)
    with pytest.raises(FileExistsError):
        scaffold_module(tmp_path, "taken", ModuleLanguage.RUST)


@pytest.mark.parametrize(
    ("language", "expected_files"),
    [
        (ModuleLanguage.PYTHON, {"__main__.py"}),
        (ModuleLanguage.RUST, {"Cargo.toml", "src/main.rs"}),
        (ModuleLanguage.CPP, {"CMakeLists.txt", "main.cpp"}),
    ],
)
def test_scaffolded_modules_verify_with_deployment_api(tmp_path: Path, language: ModuleLanguage, expected_files: set[str]) -> None:
    (tmp_path / "deploy.py").write_text(POPULATED_DEPLOY)
    result = scaffold_module(tmp_path, "sample", language)
    assert result.registered
    assert {str(path.relative_to(result.module_path)) for path in result.created_files} == expected_files

    namespace = load_deploy(tmp_path)
    declared = {module.name: module for module in namespace["get_modules"]()}
    assert set(declared) == {"control", "sample"}
    status, message = declared["sample"].verify()
    assert status.name == "SUCCESS", message
    placement = namespace["pi_name_to_process_types"](["pi"])
    assert {process.get_name() for process in placement["pi"]} == {"control-process", "sample"}


def test_python_sample_runs(tmp_path: Path) -> None:
    scaffold_module(tmp_path, "hello", ModuleLanguage.PYTHON)
    process = subprocess.Popen(
        [sys.executable, "-u", str(tmp_path / "python" / "hello" / "__main__.py")],
        stdout=subprocess.PIPE, text=True,
    )
    try:
        assert process.stdout.readline().startswith("hello started on")
        assert process.stdout.readline().strip() == "hello heartbeat 0"
    finally:
        process.kill()
        process.wait()


def test_backend_script_adds_module_to_installed_project(tmp_path: Path) -> None:
    project = tmp_path / "plain-app"
    project.mkdir()
    assert_success(run_script(INSTALLER, project, {"BLITZ_SETUP": "none"}))

    added = run_script(
        project / "scripts" / "backend.sh",
        project,
        {"BLITZ_BACKEND_ACTION": "add-module", "BLITZ_MODULE_NAME": "vision", "BLITZ_MODULE_LANGUAGE": "cpp"},
    )
    assert_success(added)
    assert "Registered ProcessType.VISION" in added.stdout
    assert (project / "backend" / "cpp" / "vision" / "CMakeLists.txt").is_file()

    imported = subprocess.run(
        [
            sys.executable, "-c",
            "from backend.deploy import get_modules, pi_name_to_process_types; "
            "assert [module.name for module in get_modules()] == ['vision']; "
            "assert [str(p) for p in pi_name_to_process_types(['pi'])['pi']] == ['vision']",
        ],
        cwd=project, env={"PYTHONPATH": str(project)}, text=True, capture_output=True, check=False,
    )
    assert imported.returncode == 0, imported.stderr

    duplicate = run_script(
        project / "scripts" / "backend.sh",
        project,
        {"BLITZ_BACKEND_ACTION": "add-module", "BLITZ_MODULE_NAME": "vision", "BLITZ_MODULE_LANGUAGE": "python"},
    )
    assert duplicate.returncode != 0
    assert "already exists" in duplicate.stderr
    assert not (project / "backend" / "python" / "vision").exists()
