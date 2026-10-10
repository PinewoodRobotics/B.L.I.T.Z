"""Simple folder declarations resolve from deploy.py rather than shell cwd."""
from pathlib import Path

import pytest

from backend.deployment.compilation.util.cpp_build import CPPBuildConfig
from backend.deployment.module.catalog import BackendModules
from backend.deployment.module.contracts import LaunchSettings, ModuleOutputs, PythonEntrypoint, TargetRequirements
from backend.deployment.module.graph import ModuleGraph
from backend.deployment.processes import WeightedProcess


class Processes(WeightedProcess):
    CONTROL = 'control-process', 1.0
    MOTOR = 'motor-process', 1.0
    TELEMETRY = 'telemetry-process', 0.2


def test_declarations_find_renamed_backend_from_deploy_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / 'project/robotBackend'
    root.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    catalog = BackendModules(root / 'deploy.py')
    modules = [
        catalog.python('control', process=Processes.CONTROL, entrypoint='main.py', dependencies=('vision',)),
        catalog.cpp_library('vision'),
        catalog.cpp('motor', process=Processes.MOTOR, executable='main'),
        catalog.rust('telemetry', process=Processes.TELEMETRY),
        catalog.rust_library('math'),
    ]
    assert catalog.backend_path == str(root)
    assert modules[0].module_folder_path == str(root / 'python/control')
    assert modules[0].entrypoint.file == 'main.py'
    assert not modules[0].launch.accepts_blitz_flags
    assert modules[1].project_root_folder_path == str(root / 'cpp/vision')
    assert modules[2].runnable_name == 'main'
    assert modules[3].project_root_folder_path == str(root / 'rust/telemetry')
    assert modules[3].runnable_name == 'telemetry'
    assert modules[4].project_root_folder_path == str(root / 'rust/math')
    assert [module.name for module in ModuleGraph(modules).ordered] == ['vision', 'control', 'motor', 'telemetry', 'math']


def test_convenience_methods_preserve_typed_contracts(tmp_path: Path) -> None:
    catalog = BackendModules(tmp_path / 'backend/deploy.py')
    outputs = ModuleOutputs(resources=('assets/*.json',))
    launch = LaunchSettings(arguments=('--mode', 'test'), accepts_blitz_flags=True)
    targets = TargetRequirements(python_versions=((3, 12),))
    entry = PythonEntrypoint(file=None, package='worker.main')
    module = catalog.python('worker', process=Processes.CONTROL, entrypoint=entry, outputs=outputs, targets=targets, launch=launch)
    assert module.entrypoint is entry
    assert module.outputs is outputs
    assert module.targets is targets
    assert module.launch is launch
    build = CPPBuildConfig('custom-build')
    assert catalog.cpp_library('vision', compilation=build).compilation_config is build
    assert catalog.cpp('motor', process=Processes.MOTOR, compilation=build).compilation_config is build
    assert catalog.cpp('motor', process=Processes.MOTOR).runnable_name == 'motor'


@pytest.mark.parametrize('name', ['common', '../outside', 'a/b', '', '.'])
def test_module_names_cannot_escape_or_claim_shared_source(name: str) -> None:
    with pytest.raises(ValueError, match='module folder name'):
        BackendModules('/tmp/backend/deploy.py').cpp_library(name)
