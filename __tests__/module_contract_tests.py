from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest

from backend.deployment.compilation.system_builder import SystemBuilder
from backend.deployment.compilation.util.systems import Architecture, LinuxDistro, PythonVersion, SystemId
from backend.deployment.module.base import Module
from backend.deployment.module.contracts import CapabilityRequirement, LaunchSettings, ModuleOutputs, PythonEntrypoint, TargetRequirements
from backend.deployment.module.graph import ModuleGraph, TargetCompatibilityError
from backend.deployment.module.supported import PythonModule
from backend.deployment.network_api.utils import FolderPath
from backend.deployment.processes import WeightedProcess
from watchdog.process_starter import OpenedProcess


class Processes(WeightedProcess):
    FIRST = 'first-process', 1.0
    SECOND = 'second-process', 1.0


def profile(**kwargs) -> SystemId:
    return SystemId('2.36', LinuxDistro.DEBIAN_12, Architecture.ARM64, PythonVersion(3, 11), **kwargs)


def test_graph_orders_dependencies_and_rejects_invalid_graphs() -> None:
    modules = [Module('program', dependencies=('a',)), Module('a', dependencies=('b',)), Module('b')]
    graph = ModuleGraph(modules)
    assert [module.name for module in graph.ordered] == ['b', 'a', 'program']
    assert graph.closure('program') == ['program', 'a', 'b']
    for invalid, message in [([Module('a'), Module('a')], 'Duplicate'), ([Module('a', dependencies=('missing',))], 'Unknown'), ([Module('a', dependencies=('b',)), Module('b', dependencies=('a',))], 'cycle')]:
        with pytest.raises(ValueError, match=message):
            ModuleGraph(invalid)


def test_target_checks_transitive_requirements_and_profiles() -> None:
    gpu = Module('gpu', targets=TargetRequirements(capabilities=(CapabilityRequirement('cuda', '12.2'),)))
    program = PythonModule('program', [], Processes.FIRST, FolderPath('.'), dependencies=('gpu',))
    graph = ModuleGraph([program, gpu, Module('portable')])
    assert [module.name for module in graph.compatible(profile())] == ['portable']
    with pytest.raises(TargetCompatibilityError, match='program -> gpu: missing capability cuda'):
        graph.validate_processes(['first-process'], profile())
    capable = profile(capabilities=(('cuda', '12.3'),))
    graph.validate_processes(['first-process'], capable)
    assert SystemId.from_build_key(capable.to_build_key()) == capable
    assert capable.to_build_key() != profile().to_build_key()
    assert TargetRequirements(architectures=(Architecture.AARCH64,)).incompatibilities(profile()) == []
    assert TargetRequirements(python_versions=((3, 12),)).incompatibilities(profile()) == ['Python 3.11']
    assert TargetRequirements(capabilities=(CapabilityRequirement('cuda', '12.2.0'),)).incompatibilities(profile(capabilities=(('cuda', '12.2'),))) == []


def test_two_python_entries_launch_from_unrelated_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd) -> None:
    blitz = tmp_path / 'blitz with spaces'
    interpreter = blitz / '.venv' / 'bin' / 'python'
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    bundle = blitz / 'backend'
    modules = []
    for module_id, entry, process in [('module-one', 'main.py', Processes.FIRST), ('module-two', 'other.py', Processes.SECOND)]:
        source = bundle / 'python' / module_id
        (source / 'assets').mkdir(parents=True)
        (source / 'assets' / 'value.txt').write_text(module_id)
        (source / entry).write_text('from pathlib import Path\nimport os, sys\nprint(Path("assets/value.txt").read_text(), sys.argv[1], os.environ["BLITZ_SYSTEM_NAME"])\n')
        modules.append(PythonModule(module_id, [], process, FolderPath(str(source)), entrypoint=PythonEntrypoint(file=entry), launch=LaunchSettings(arguments=('argument with spaces',), accepts_blitz_flags=False)))
    monkeypatch.chdir(tmp_path)
    for module in modules:
        assert module.verify()[0].value == 'success'
        child = OpenedProcess.start_module(module, str(bundle), {'blitz-path': str(blitz), 'system-name': 'test-pi'})
        child.wait(timeout=10)
        assert child.returncode == 0
        assert f"{module.name} argument with spaces test-pi" in capfd.readouterr().out
    assert [module.get_process_name() for module in modules] == ['first-process', 'second-process']


def test_runtime_library_paths_are_scoped_and_transitive(tmp_path: Path) -> None:
    module = PythonModule('app', [], Processes.FIRST, FolderPath('.'))
    manifest = {'modules': {'app': {'library_paths': ['lib/app', 'lib/a', 'lib/b', 'deps/native/a']}}}
    (tmp_path / 'runtime-manifest.json').write_text(json.dumps(manifest))
    env = module.get_run_environment(FolderPath(str(tmp_path)))
    assert env['LD_LIBRARY_PATH'].split(os.pathsep) == [str(tmp_path / path) for path in ['lib/app', 'lib/a', 'lib/b', 'deps/native/a', 'deps/native']]
    assert env['BLITZ_RESOURCE_DIR'] == str(tmp_path / 'resources' / 'app')
    with pytest.raises(ValueError, match='unavailable'):
        PythonModule('missing', [], Processes.SECOND, FolderPath('.')).get_run_environment(FolderPath(str(tmp_path)))


def test_entrypoints_and_launch_paths_cannot_escape_module() -> None:
    with pytest.raises(ValueError):
        PythonEntrypoint(file='../outside.py')
    with pytest.raises(ValueError):
        LaunchSettings(working_directory='/tmp')
    with pytest.raises(ValueError):
        PythonEntrypoint(file='main.py', package='pkg')
    package = PythonModule('package', [], Processes.FIRST, FolderPath('.'), entrypoint=PythonEntrypoint(file=None, package='pkg.worker'))
    assert package.get_run_argv(FolderPath('/blitz/backend'), '/blitz')[2:4] == ['-m', 'pkg.worker']


def test_assigned_incompatible_process_fails_before_docker_or_transfer(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.deployment.deployer import BlitzNetworkDeployer
    from backend.deployment.network_api.system_api import System
    from backend.deployment.network_api.catalog import SystemCatalog
    device = System(SystemCatalog('pi.local', 'pi', 9999, 8080, FolderPath('/blitz'), 'aarch64', 'Linux-glibc2.36', 3, 11, 'debian', None, '12'))
    gpu = Module('gpu', targets=TargetRequirements(capabilities=(CapabilityRequirement('cuda'),)))
    program = PythonModule('program', [], Processes.FIRST, FolderPath('.'), dependencies=('gpu',))
    monkeypatch.setattr(BlitzNetworkDeployer, '_find_systems', lambda _: {device})
    monkeypatch.setattr(BlitzNetworkDeployer, 'prepare_systems', lambda *_: pytest.fail('prepared Docker before target validation'))
    monkeypatch.setattr(BlitzNetworkDeployer, 'distribute', lambda *_: pytest.fail('transferred incompatible bundle'))
    with pytest.raises(TargetCompatibilityError, match='program -> gpu'):
        BlitzNetworkDeployer.deploy([program, gpu], lambda _: {'pi': [Processes.FIRST]})


def test_artifact_exports_headers_resources_and_rejects_conflicts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.deployment.compilation import build_artifacts
    monkeypatch.setattr(build_artifacts, 'ROOT', tmp_path / 'artifacts')
    source = tmp_path / 'source'
    (source / 'include').mkdir(parents=True)
    (source / 'include' / 'api.h').write_text('int value(void);')
    (source / 'assets').mkdir()
    (source / 'assets' / 'model.txt').write_text('model')
    artifact = tmp_path / 'artifacts' / 'cpp' / 'a'
    artifact.mkdir(parents=True)
    (artifact / 'libcommon.so').write_bytes(b'first')
    step = {'module': 'a', 'language': 'cpp', 'source': str(source), 'outputs': {'headers': ['include/*.h'], 'resources': ['assets/*.txt']}}
    build_artifacts.export(step)
    assert (tmp_path / 'artifacts' / 'include' / 'a' / 'include' / 'api.h').is_file()
    assert (artifact / 'assets' / 'model.txt').read_text() == 'model'
    assert (tmp_path / 'artifacts' / 'resources' / 'a' / 'assets' / 'model.txt').read_text() == 'model'
    other = tmp_path / 'artifacts' / 'lib' / 'b'
    other.mkdir(parents=True)
    (other / 'libcommon.so').write_bytes(b'second')
    with pytest.raises(ValueError, match='Conflicting library libcommon.so.*consumer'):
        build_artifacts.validate_collisions([tmp_path / 'artifacts' / 'lib' / 'a', other], 'consumer')
    with pytest.raises(ValueError, match='Declared output missing'):
        build_artifacts.checked_matches(source, 'missing/*.h')
    with pytest.raises(ValueError, match='Unsafe artifact pattern'):
        build_artifacts.checked_matches(source, '../outside')


def test_cuda_compiler_validates_cached_toolkit_against_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess
    from backend.deployment.compilation.build_artifacts import validate_toolkit
    step = {'module': 'cuda-library', 'target_capabilities': [{'name': 'cuda', 'minimum_version': '12.2'}]}
    plan = {'system': {'capabilities': {'cuda': '12.3'}}}
    monkeypatch.setattr(subprocess, 'run', lambda *_, **__: subprocess.CompletedProcess([], 0, 'Cuda compilation tools, release 12.2, V12.2.140'))
    validate_toolkit(step, plan)
    with pytest.raises(ValueError, match='exceeds target driver support'):
        validate_toolkit(step, {'system': {'capabilities': {'cuda': '12.1'}}})
    monkeypatch.setattr(subprocess, 'run', lambda *_, **__: subprocess.CompletedProcess([], 0, 'release 11.8'))
    with pytest.raises(ValueError, match='below required'):
        validate_toolkit(step, plan)
    def missing(*_, **__):
        raise FileNotFoundError('nvcc')
    monkeypatch.setattr(subprocess, 'run', missing)
    with pytest.raises(ValueError, match='no usable nvcc'):
        validate_toolkit(step, plan)


def test_new_entrypoint_and_resource_changes_reuse_dependency_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'main.py').write_text('print(1)')
    (source / 'other.py').write_text('print(2)')
    (source / 'value.txt').write_text('first')
    (tmp_path / 'requirements.txt').write_text('# shared\n')
    monkeypatch.chdir(tmp_path)
    module = PythonModule('app', [], Processes.FIRST, FolderPath(str(source)), entrypoint=PythonEntrypoint(file='main.py'), outputs=ModuleOutputs(resources=('value.txt',)))
    builder = SystemBuilder(profile(), FolderPath(str(tmp_path / 'build' / 'artifacts')), FolderPath(str(tmp_path / 'build' / 'contexts' / 'test')))
    builder.prepare([module], True)
    image = builder.dependency_image()
    module.entrypoint = PythonEntrypoint(file='other.py')
    (source / 'value.txt').write_text('second')
    builder.prepare([module], True)
    assert builder.dependency_image() == image
    module.dependencies = ('missing',)
    with pytest.raises(ValueError, match='Unknown module dependency'):
        builder.prepare([module], True)


def test_provision_plan_keeps_legacy_shape_for_existing_cache_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / 'python'
    source.mkdir()
    (source / '__main__.py').write_text('print(1)')
    (tmp_path / 'requirements.txt').write_text('# shared\n')
    monkeypatch.chdir(tmp_path)
    module = PythonModule('app', [], Processes.FIRST, FolderPath(str(source)))
    builder = SystemBuilder(profile(), FolderPath(str(tmp_path / 'build' / 'artifacts')), FolderPath(str(tmp_path / 'build' / 'contexts' / 'test')))
    builder.prepare([module], True)
    provision = json.loads((builder.context / 'provision-plan.json').read_text())
    assert 'capabilities' not in provision['system']
    for step in provision['steps']:
        assert set(step) == {'id', 'kind', 'requires', 'module', 'language', 'source', 'command', 'libraries', 'extra_commands', 'binary'}
    assert all('dependencies' not in step for step in provision['steps'])


def test_nested_library_and_header_exports_are_in_build_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.deployment.compilation import build_artifacts
    monkeypatch.setattr(build_artifacts, 'ROOT', tmp_path)
    libraries = tmp_path / 'lib' / 'provider' / 'nested'
    libraries.mkdir(parents=True)
    (libraries / 'libprovider.so').write_bytes(b'library')
    headers = tmp_path / 'include' / 'provider' / 'include'
    headers.mkdir(parents=True)
    (headers / 'api.h').write_text('int value(void);')
    environment = build_artifacts.build_environment({'module': 'consumer', 'dependencies': ['provider']})
    assert str(libraries) in environment['libraries'].split(os.pathsep)
    assert str(headers) in environment['headers'].split(os.pathsep)


def test_explicit_environment_is_preserved_without_inheriting_host_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('LD_LIBRARY_PATH', '/host-only')
    module = PythonModule('app', [], Processes.FIRST, FolderPath('.'), launch=LaunchSettings(environment=(('LD_LIBRARY_PATH', '/vendor'), ('MODE', 'test'))))
    environment = module.get_run_environment(FolderPath(str(tmp_path)))
    assert environment['MODE'] == 'test'
    assert environment['LD_LIBRARY_PATH'].endswith(os.pathsep + '/vendor')
    assert '/host-only' not in environment['LD_LIBRARY_PATH']
