"""Backend source boundaries and shared code are deployment contracts."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from backend.deployment.compilation.system_builder import SystemBuilder
from backend.deployment.compilation.util.systems import Architecture, LinuxDistro, PythonVersion, SystemId
from backend.deployment.module.layout import validate_backend_layout
from backend.deployment.module.graph import ModuleGraph
from backend.deployment.module.supported import PythonModule
from backend.deployment.network_api.utils import FolderPath


def python_module(source: Path, name: str = 'app') -> PythonModule:
    return PythonModule(name, [], None, FolderPath(str(source)))


def test_one_module_owns_each_complete_folder(tmp_path: Path) -> None:
    source = tmp_path / 'backend/python/app'
    source.mkdir(parents=True)
    alias = tmp_path / 'alias'
    alias.symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError, match='One module per source folder: first and second'):
        ModuleGraph([python_module(source, 'first'), python_module(alias, 'second')])


@pytest.mark.parametrize('relative', ['outside/app', 'backend/app', 'backend/cpp/app', 'backend/python/common', 'backend/python/group/app'])
def test_module_sources_require_the_backend_language_layout(tmp_path: Path, relative: str) -> None:
    source = tmp_path / relative
    source.mkdir(parents=True)
    with pytest.raises(ValueError, match='must live in'):
        validate_backend_layout([python_module(source)], str(tmp_path / 'backend'))


def test_source_symlinks_cannot_escape_backend(tmp_path: Path) -> None:
    source = tmp_path / 'backend/python/app'
    source.mkdir(parents=True)
    outside = tmp_path / 'private.py'
    outside.write_text('secret = 1\n')
    (source / 'external.py').symlink_to(outside)
    with pytest.raises(ValueError, match='symlink escapes'):
        validate_backend_layout([python_module(source)], str(tmp_path / 'backend'))


def test_common_is_staged_without_sibling_python_imports(tmp_path: Path) -> None:
    backend = tmp_path / 'backend'
    for name in ('app', 'sibling', 'common'):
        (backend / 'python' / name).mkdir(parents=True)
    (backend / 'python/common/__init__.py').write_text('VALUE = 42\n')
    (backend / 'python/sibling/__init__.py').write_text('VALUE = 99\n')
    (backend / 'python/app/__main__.py').write_text(
        'from common import VALUE\n'
        'import importlib.util\n'
        'assert importlib.util.find_spec("sibling") is None\n'
        'print(VALUE)\n'
    )
    module = python_module(backend / 'python/app')
    system = SystemId('2.36', LinuxDistro.DEBIAN_12, Architecture.AMD64, PythonVersion(3, 11))
    builder = SystemBuilder(system, FolderPath(str(tmp_path / 'artifacts')), FolderPath(str(tmp_path / 'context')), FolderPath(str(backend)))
    plan = builder.create_plan([module], False)
    source = builder.context / next(step.source for step in plan.steps if step.module == 'app').removeprefix('/work/')
    result = subprocess.run([sys.executable, str(source / '__main__.py')], cwd=tmp_path, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == '42'
    assert not (builder.context / 'workspace/python/sibling').exists()
    # Even an old manifest with transitive source paths cannot expose a sibling.
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    (bundle / 'runtime-manifest.json').write_text(json.dumps({'modules': {'app': {'module_paths': ['python/app', 'python/sibling'], 'library_paths': []}}}))
    environment = module.get_run_environment(FolderPath(str(bundle)))
    assert str(bundle / 'python/sibling') not in environment['PYTHONPATH'].split(':')
    (source / 'common/__init__.py').write_text('VALUE = 100\n')
    with pytest.raises(ValueError, match='shadows shared'):
        (backend / 'python/app/common').mkdir()
        builder.create_plan([module], False)
