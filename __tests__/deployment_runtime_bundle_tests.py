"""Run: .venv/bin/python -m pytest __tests__/deployment_runtime_bundle_tests.py"""

import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

from backend.deployment.bundler import CodeBundler
from backend.deployment.compilation.system_builder import SystemBuilder
from backend.deployment.compilation.util.systems import (
    Architecture, LinuxDistro, PythonVersion, SystemId,
)
from backend.deployment.network_api.utils import FolderPath


ROOT = Path(__file__).resolve().parents[1]


def test_bundle_carries_matching_api_without_bytecode(tmp_path, monkeypatch):
    backend = tmp_path / 'source'
    backend.mkdir()
    (backend / 'deploy.py').write_text('# deployment declarations\n')
    profile = SystemId('2.39', LinuxDistro.UBUNTU_24, Architecture.AMD64, PythonVersion(3, 12))
    bundler = CodeBundler(
        [], FolderPath(str(backend)), FolderPath(str(tmp_path / 'build')),
        FolderPath(str(tmp_path / 'outputs')), profile,
    )
    context = Path(bundler.context_path)
    context.mkdir(parents=True)
    (context / 'build-plan.json').write_text(json.dumps({'steps': []}))
    monkeypatch.setattr(SystemBuilder, 'build_prepared', lambda *args, **kwargs: None)
    with ZipFile(bundler.bundle(prepared=True)) as archive:
        prefix = profile.to_build_key() + '/deployment/'
        assert archive.read(prefix + 'module/catalog.py') == (
            ROOT / 'backend/deployment/module/catalog.py'
        ).read_bytes()
        assert len(archive.read(prefix + '.blitz-runtime-id').strip()) == 64
        assert not any('__pycache__' in name or name.endswith('.pyc') for name in archive.namelist())


def test_watchdog_reimports_replaced_deployment_library(tmp_path):
    # Use a separate interpreter so replacing backend modules cannot affect the
    # pytest process or the module instances created by other tests.
    script = r'''
import importlib
from pathlib import Path
import shutil
import sys

root, target = map(Path, sys.argv[1:])
backend = target / 'backend'
runtime = backend / 'deployment'
runtime.mkdir(parents=True)
(backend / '__init__.py').write_text('')
(runtime / '__init__.py').write_text('')
(runtime / 'processes.py').write_text('old_api = True\n')
(runtime / '.blitz-runtime-id').write_text('old')
sys.path.insert(0, str(target))
from watchdog.util.lazy_importer import _import_or_reload_module
old = _import_or_reload_module('backend.deployment.processes')
assert old.old_api

shutil.rmtree(runtime)
shutil.copytree(root / 'backend/deployment', runtime,
               ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
(runtime / '.blitz-runtime-id').write_text('replacement')
process = backend / 'python/sample'
process.mkdir(parents=True)
(process / '__main__.py').write_text('')
(backend / 'deploy.py').write_text(
    'from backend.deployment.module.catalog import BackendModules\n'
    'from backend.deployment.processes import WeightedProcess\n'
    'class Process(WeightedProcess):\n'
    '    SAMPLE = "sample", 1.0\n'
    'modules = BackendModules(__file__)\n'
    'def get_modules():\n'
    '    return [modules.python("sample", process=Process.SAMPLE)]\n'
)
from watchdog.ext.expected_deployment_struct import get_modules, Module
modules = get_modules()
assert [module.name for module in modules] == ['sample']
assert isinstance(modules[0], Module)
assert not hasattr(importlib.import_module('backend.deployment.processes'), 'old_api')
'''
    result = subprocess.run(
        [sys.executable, '-c', script, str(ROOT), str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
