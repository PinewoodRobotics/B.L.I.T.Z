"""Actual offline container builds and launches for module contracts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import runpy
import subprocess
from typing import NamedTuple

import pytest

from __tests__.docker_resources import DockerTestResources
from backend.deployment.bundler import CodeBundler
from backend.deployment.compilation.system_builder import SystemBuilder
from backend.deployment.compilation.util.systems import Architecture, LinuxDistro, PythonVersion, SystemId
from backend.deployment.network_api.utils import FolderPath
from backend.deployment.module.base import Module

SAMPLE = Path(__file__).parent / 'fixtures' / 'module_contract_backend'


class ContractBundle(NamedTuple):
    root: Path
    system: SystemId
    image: str
    modules: list[Module]


@pytest.fixture(scope='module')
def contract_bundle(tmp_path_factory: pytest.TempPathFactory, docker_builds: DockerTestResources) -> ContractBundle:
    root = tmp_path_factory.mktemp('module-contracts')
    modules = runpy.run_path(str(SAMPLE / 'deploy.py'))['get_modules']()
    system = SystemId('2.39', LinuxDistro.UBUNTU_24, Architecture.from_machine(platform.machine()), PythonVersion(3, 12))
    bundler = CodeBundler(modules, FolderPath(str(SAMPLE)), FolderPath(str(root / 'build')), FolderPath(str(root / 'outputs')), system)
    previous = Path.cwd()
    try:
        os.chdir(SAMPLE)
        archive = bundler.bundle()
    finally:
        os.chdir(previous)
    subprocess.run(['unzip', '-q', archive, '-d', str(root / 'extracted')], check=True)
    builder = SystemBuilder(system, bundler.build_path, bundler.context_path)
    return ContractBundle(root / 'extracted', system, builder.dependency_image(), modules)


def run_module(bundle: ContractBundle, name: str) -> str:
    root, system, image, modules = bundle
    module = next(module for module in modules if module.name == name)
    bundle_path = Path('/bundle') / system.to_build_key()
    # Resolve exactly the same declared argv, cwd and environment as watchdog.
    root_on_host = root / system.to_build_key()
    environment = module.get_run_environment(FolderPath(str(root_on_host)))
    environment = {key: value.replace(str(root_on_host), str(bundle_path)) for key, value in environment.items()}
    command = ['docker', 'run', '--rm', '--network', 'none', '--platform', system.docker_image,
        '--mount', f'type=bind,src={root},dst=/bundle,readonly', '--workdir', module.get_run_directory(FolderPath(str(bundle_path)))]
    for key, value in environment.items():
        command += ['--env', f'{key}={value}']
    argv = module.get_run_argv(FolderPath(str(bundle_path)), '/tmp')
    if module.get_language_name() == 'python':
        argv[0] = '/usr/bin/python3'
    result = subprocess.run([*command, image, *argv], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


def test_executable_loads_transitive_libraries_without_absolute_paths(contract_bundle: ContractBundle) -> None:
    assert run_module(contract_bundle, 'program') == '42'


def test_same_soname_is_isolated_between_python_processes_and_resources_work(contract_bundle: ContractBundle) -> None:
    assert run_module(contract_bundle, 'python-one') == '100 resource-ok resource-ok'
    assert run_module(contract_bundle, 'python-two') == '200'
    root, system, _, _ = contract_bundle
    manifest = json.loads((root / system.to_build_key() / 'runtime-manifest.json').read_text())
    assert 'lib/common_two' not in manifest['modules']['python-one']['library_paths']


def test_generated_namespace_is_shared_and_bundled_once(contract_bundle: ContractBundle) -> None:
    root, system, _, _ = contract_bundle
    bundle = root / system.to_build_key()
    files = list(bundle.rglob('portable.py'))
    assert files == [bundle / 'shared/backend/generated/messages/portable.py']
    assert (bundle / 'shared/backend/generated/messages/schema.txt').read_text().strip() == 'portable-schema'
    # Both independently launched Python entrypoints import backend.generated.
    assert run_module(contract_bundle, 'python-one') == '100 resource-ok resource-ok'
    assert run_module(contract_bundle, 'python-two') == '200'


def test_same_soname_in_one_closure_fails_even_with_different_filenames(contract_bundle: ContractBundle) -> None:
    root, system, image, _ = contract_bundle
    helper = Path(__file__).resolve().parents[1] / 'backend' / 'deployment' / 'compilation' / 'build_artifacts.py'
    first = f'/bundle/{system.to_build_key()}/lib/common_one/libcommon.so'
    second = f'/bundle/{system.to_build_key()}/lib/common_two/libcommon.so'
    python = (
        'import runpy, shutil; from pathlib import Path; '
        f'shutil.copy2({first!r}, "/tmp/libfirst.so"); '
        f'shutil.copy2({second!r}, "/tmp/libsecond.so"); '
        'helper = runpy.run_path("/helper.py"); '
        'helper["validate_collisions"]([Path("/tmp")], "combined-process")'
    )
    result = subprocess.run([
        'docker', 'run', '--rm', '--network', 'none', '--platform', system.docker_image,
        '--mount', f'type=bind,src={root},dst=/bundle,readonly',
        '--mount', f'type=bind,src={helper},dst=/helper.py,readonly',
        image, 'python3', '-c', python,
    ], capture_output=True, text=True)
    assert result.returncode != 0
    assert 'Conflicting library libcommon.so in dependency closure of combined-process' in result.stderr
