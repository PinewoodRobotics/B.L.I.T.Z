"""Execute target install commands to verify replacement and transfer cleanup."""
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile

import pytest

from backend.deployment.network_api.system_api import System
from backend.deployment.network_api.utils import FilePath, FolderPath
from backend.deployment.network_api.zeroconf import DiscoveredNetworkSystem
from backend.deployment.rsyncer import Rsyncer


class LocalTarget(System):
    def run_command(self, command: str) -> bool:
        return subprocess.run(['bash', '-c', command], capture_output=True).returncode == 0

    def deploy_file(self, local_file_path: FilePath, remote_file_path: FilePath) -> bool:
        Path(remote_file_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_file_path, remote_file_path)
        return True


def target(root: Path) -> LocalTarget:
    return LocalTarget(DiscoveredNetworkSystem(
        hostname='test.local', system_name='test', watchdog_port=9999, autobahn_port=8080,
        blitz_path=FolderPath(str(root)), machine_architecture='aarch64',
        platform_description='Linux-with-glibc2.36', python_major_version=3, python_minor_version=11,
        os_distribution_id='debian', os_distribution_version_id='12',
    ))


def write_bundle(output: Path, system: System, files: dict[str, str]) -> Path:
    key = system.general_info.to_system_id().to_build_key()
    output.mkdir(exist_ok=True)
    path = output / f'{key}.zip'
    with ZipFile(path, 'w') as archive:
        for name, contents in files.items():
            archive.writestr(f'{key}/{name}', contents)
    return path


def test_redeploy_removes_old_modules_resources_and_transfer_bundles(tmp_path: Path) -> None:
    system = target(tmp_path / 'target with spaces')
    backend = Path(system.general_info.blitz_path) / 'backend'
    (backend / 'deployment').mkdir(parents=True)
    (backend / 'deployment/framework.py').write_text('keep infrastructure')
    (backend / '__init__.py').write_text('# package\n')
    output = tmp_path / 'outputs'
    sync = Rsyncer([], FolderPath(str(output)), FolderPath('bundles'), {system})
    write_bundle(output, system, {'python/old/main.py': 'old', 'lib/old/libold.so': 'old', 'deploy.py': 'old'})
    sync.deploy()
    assert (backend / 'python/old/main.py').exists()
    transfers = backend.parent / 'bundles'
    assert not list(transfers.iterdir())
    # A legacy profile archive and its extracted folder must also be retired.
    (transfers / 'legacy.zip').write_text('old archive')
    (transfers / 'legacy').mkdir()
    (transfers / 'legacy/stale').write_text('old bundle')
    write_bundle(output, system, {'python/new/main.py': 'new', 'deploy.py': 'new'})
    sync.deploy()
    assert (backend / 'python/new/main.py').read_text() == 'new'
    assert not (backend / 'python/old').exists()
    assert not (backend / 'lib').exists()
    assert (backend / 'deployment/framework.py').read_text() == 'keep infrastructure'
    assert (backend / '__init__.py').exists()
    assert not list(transfers.iterdir())


def test_invalid_archive_keeps_active_bundle_and_cleans_extraction(tmp_path: Path) -> None:
    system = target(tmp_path / 'target')
    backend = Path(system.general_info.blitz_path) / 'backend'
    backend.mkdir(parents=True)
    (backend / 'deploy.py').write_text('active')
    output = tmp_path / 'outputs'
    archive = write_bundle(output, system, {'deploy.py': 'replacement'})
    archive.write_text('not a zip')
    sync = Rsyncer([], FolderPath(str(output)), FolderPath('bundles'), {system})
    with pytest.raises(RuntimeError, match='Failed to install bundle'):
        sync.deploy()
    assert (backend / 'deploy.py').read_text() == 'active'
    assert not list((backend.parent / 'bundles').glob('.install.*'))


def test_bundle_installs_matching_deployment_api_and_removes_old_files(tmp_path: Path) -> None:
    system = target(tmp_path / 'target with spaces')
    backend = Path(system.general_info.blitz_path) / 'backend'
    (backend / 'deployment/__pycache__').mkdir(parents=True)
    (backend / 'deployment/obsolete.py').write_text('old API')
    (backend / 'deployment/__pycache__/cached.pyc').write_bytes(b'old cache')
    (backend / '__init__.py').write_text('# preserved package\n')
    output = tmp_path / 'outputs'
    write_bundle(output, system, {
        'deployment/module/catalog.py': 'matching API',
        'deployment/.blitz-runtime-id': 'new revision',
        'deploy.py': 'new declarations',
    })
    Rsyncer([], FolderPath(str(output)), FolderPath('bundles'), {system}).deploy()
    assert (backend / 'deployment/module/catalog.py').read_text() == 'matching API'
    assert not (backend / 'deployment/obsolete.py').exists()
    assert not (backend / 'deployment/__pycache__').exists()
    assert (backend / '__init__.py').read_text() == '# preserved package\n'


def test_dependency_failure_keeps_transfer_for_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    system = target(tmp_path / 'target')
    output = tmp_path / 'outputs'
    archive = write_bundle(output, system, {'deploy.py': 'replacement'})
    sync = Rsyncer([], FolderPath(str(output)), FolderPath('bundles'), {system}, are_deps_bundled=True)
    def fail_dependencies(_system: System) -> None:
        raise RuntimeError('dependency installation failed')
    monkeypatch.setattr(sync, 'install_dependencies', fail_dependencies)
    with pytest.raises(RuntimeError, match='dependency installation failed'):
        sync.deploy()
    assert (Path(system.general_info.blitz_path) / 'bundles' / archive.name).exists()


@pytest.mark.parametrize('path', ['', '.', '../bundles', 'backend', 'backend/transfers'])
def test_transfer_cleanup_cannot_target_backend_or_parent(path: str) -> None:
    with pytest.raises(ValueError, match='dedicated folder'):
        Rsyncer([], FolderPath('outputs'), FolderPath(path), set())
