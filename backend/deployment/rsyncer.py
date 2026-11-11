import os
import posixpath
import shlex
from pathlib import Path, PurePosixPath
import re

from backend.deployment.misc.report import stage

from backend.deployment.bundle_manifest import (
    DELTA_FOLDER,
    MANIFEST_NAME,
    BundleManifest,
    compare,
    read_manifest,
    write_delta_archive,
)

from backend.deployment.module.graph import ModuleGraph
from backend.deployment.module.base import DependencyInstallation, Module, matches_module_type
from backend.deployment.network_api.system_api import System
from backend.deployment.network_api.utils import FilePath, FolderPath
from backend.deployment.network_api.catalog import SystemCatalog


class Rsyncer:
    def __init__(
        self,
        modules: list[Module],
        local_bundler_output_path: FolderPath,
        backend_bundle_path: FolderPath,
        systems: set[System],
        are_deps_bundled: bool = False,
        system_host_to_pass_user: dict[str, tuple[str, str]] | None = None,
        incremental: bool = True,
    ):
        self.modules: list[Module] = modules
        self.local_bundler_output_path: FolderPath = local_bundler_output_path
        self.backend_bundle_path: FolderPath = backend_bundle_path
        self.systems: set[System] = systems
        self.system_host_to_pass_user: dict[str, tuple[str, str]] | None = (
            system_host_to_pass_user
        )
        self.are_deps_bundled: bool = are_deps_bundled
        self.incremental: bool = incremental
        transfer_path = PurePosixPath(self.backend_bundle_path.strip('/'))
        if not transfer_path.parts or '..' in transfer_path.parts or transfer_path.parts[0] == 'backend':
            raise ValueError('Bundle transfers require a dedicated folder outside backend/')

    def deploy(self) -> None:
        for system in sorted(self.systems, key=self._system_label):
            self._apply_system_credentials(system)
            label = self._system_label(system)
            log_dir = Path(self.local_bundler_output_path) / "logs" / re.sub(r"[^a-zA-Z0-9_.-]", "_", label)
            name, archive = self.get_bundled_zip(system.general_info)
            bundle = read_manifest(Path(archive), name.removesuffix(".zip"))
            installed: tuple[BundleManifest, str] | None = None
            if self.incremental and bundle is not None:
                with stage(f"{label}: compare installed bundle", log_dir / "compare.log"):
                    installed = self.read_installed_manifest(system, bundle)
            if installed is None:
                with stage(f"{label}: transfer bundle", log_dir / "transfer.log"):
                    name, remote_zip_path = self.rsync_bundle_zip(system)
                with stage(f"{label}: install bundle", log_dir / "install.log"):
                    self.install_bundle(system, name, FilePath(remote_zip_path))
            else:
                assert bundle is not None
                self.deploy_delta(system, label, log_dir, bundle, *installed)
            if self.are_deps_bundled:
                digest = bundle.dependency_digest() if bundle is not None else None
                if digest is not None and self.incremental and self.dependencies_current(system, digest):
                    print(f"[ OK ] {label}: dependencies unchanged; skipped installation")
                else:
                    with stage(f"{label}: install dependencies", log_dir / "dependencies.log"):
                        self.install_dependencies(system)
                        if digest is not None:
                            self.record_dependencies(system, digest)
            with stage(f"{label}: clean transfer files", log_dir / "cleanup.log"):
                self.cleanup_bundle_transfers(system)
            print(f"       Remote command logs: {log_dir}")

    def _remote_backend(self, system: System) -> str:
        return posixpath.join(system.general_info.blitz_path, "backend")

    def _dependency_marker(self, system: System) -> str:
        # Kept inside the environment it describes: a rebuilt venv loses it.
        return posixpath.join(system.general_info.blitz_path, ".venv", ".blitz-dependencies")

    def read_installed_manifest(
        self, system: System, bundle: BundleManifest
    ) -> tuple[BundleManifest, str] | None:
        """Return the target's installed manifest and exact text, if it can be trusted."""
        path = posixpath.join(self._remote_backend(system), MANIFEST_NAME)
        text = system.read_file(FilePath(path))
        if text is None:
            print("       No installed bundle manifest; transferring the complete bundle")
            return None
        installed = BundleManifest.from_json(text)
        if installed is None or installed.system != bundle.system:
            print("       Installed bundle manifest is unusable; transferring the complete bundle")
            return None
        return installed, text

    def deploy_delta(
        self,
        system: System,
        label: str,
        log_dir: Path,
        bundle: BundleManifest,
        installed: BundleManifest,
        installed_text: str,
    ) -> None:
        delta = compare(installed, bundle)
        if delta.empty:
            with stage(f"{label}: installed bundle is current; clear runtime caches", log_dir / "install.log"):
                if not system.run_command(f"set -e\n{self._clear_runtime_caches(system)}"):
                    raise RuntimeError(
                        f"Failed to clear runtime caches on {system.general_info.hostname}"
                    )
            return
        name, archive = self.get_bundled_zip(system.general_info)
        delta_archive = Path(self.local_bundler_output_path) / "incremental" / name
        payload = write_delta_archive(
            Path(archive), delta_archive, name.removesuffix(".zip"), delta, installed_text
        )
        total = sum(entry.size for entry in bundle.files.values())
        print(
            f"       Changed {len(delta.changed)} of {len(bundle.files)} files "
            f"({payload / 1e6:.1f} of {total / 1e6:.1f} MB); removed {len(delta.removed)}"
        )
        try:
            with stage(f"{label}: transfer changed files", log_dir / "transfer.log"):
                _, remote_zip_path = self.rsync_bundle_zip(system, FilePath(str(delta_archive)))
            with stage(f"{label}: install changed files", log_dir / "install.log"):
                self.install_delta(system, name, FilePath(remote_zip_path))
        finally:
            delta_archive.unlink(missing_ok=True)

    def _clear_runtime_caches(self, system: System) -> str:
        """Match a complete install, whose --delete removes runtime bytecode.

        Installed files keep archive timestamps, so a same-size edit could
        otherwise leave Python trusting stale bytecode.
        """
        backend = shlex.quote(self._remote_backend(system))
        return f"find {backend} -type d -name __pycache__ -prune -exec rm -rf -- {{}} +"

    def dependencies_current(self, system: System, digest: str) -> bool:
        recorded = system.read_file(FilePath(self._dependency_marker(system)))
        return recorded is not None and recorded.strip() == digest

    def record_dependencies(self, system: System, digest: str) -> None:
        marker = self._dependency_marker(system)
        directory = shlex.quote(posixpath.dirname(marker))
        command = (
            f"if [ -d {directory} ]; then "
            f"printf '%s\\n' {shlex.quote(digest)} > {shlex.quote(marker)}; fi"
        )
        if not system.run_command(command):
            # Only costs a reinstall next time; installation itself succeeded.
            print(f"[WARN] Could not record installed dependencies on {system.general_info.hostname}")

    def install_dependencies(self, system: System) -> None:
        installed_deps_lang_names: set[str] = set()
        for module in ModuleGraph(self.modules).compatible(system.general_info.to_system_id()):
            if not matches_module_type(module, DependencyInstallation):
                continue

            if (
                module.get_language_name() in installed_deps_lang_names
                and not module.should_rerun_for_each_module()
            ):
                continue

            remote_backend_path = FolderPath(
                posixpath.join(system.general_info.blitz_path, "backend")
            )
            installed = system.run_command(
                module.get_dependency_installation_command(
                    system.general_info.blitz_path,
                    remote_backend_path,
                )
            )
            if not installed:
                raise RuntimeError(
                    f"Failed to install dependencies on {system.general_info.hostname}"
                )
            installed_deps_lang_names.add(module.get_language_name())

    def rsync_bundle_zip(
        self, system: System, zip_path: FilePath | None = None
    ) -> tuple[str, FilePath]:
        name, bundle_path = self.get_bundled_zip(system.general_info)
        zip_path = zip_path or bundle_path
        remote_bundle_dir = FolderPath(
            posixpath.join(
                system.general_info.blitz_path, self.backend_bundle_path.strip("/")
            )
        )
        remote_zip_path = FilePath(posixpath.join(remote_bundle_dir, name))
        deployed = system.deploy_file(
            zip_path,
            remote_zip_path,
        )

        if not deployed:
            raise RuntimeError(
                f"Failed to deploy bundle to {system.general_info.hostname}"
            )

        return name, remote_zip_path

    def install_bundle(
        self,
        system: System,
        name: str,
        remote_zip_path: FilePath,
    ) -> None:
        remote_backend_path = FolderPath(
            posixpath.join(system.general_info.blitz_path, "backend")
        )
        remote_bundle_dir = FolderPath(
            posixpath.join(
                system.general_info.blitz_path, self.backend_bundle_path.strip("/")
            )
        )
        bundle_dir_name = name[:-4] if name.endswith(".zip") else name
        manifest = shlex.quote(posixpath.join(remote_backend_path, MANIFEST_NAME))
        command = f"""
        set -e
        staging=$(mktemp -d {shlex.quote(posixpath.join(remote_bundle_dir, '.install.XXXXXX'))})
        trap 'rm -rf -- "$staging"' EXIT
        unzip -o {shlex.quote(remote_zip_path)} -d "$staging"
        test -d "$staging"/{shlex.quote(bundle_dir_name)}
        mkdir -p {shlex.quote(remote_backend_path)}
        rm -f -- {manifest}
        if [ -d "$staging"/{shlex.quote(bundle_dir_name)}/deployment ]; then
            rsync -a --delete -- "$staging"/{shlex.quote(bundle_dir_name)}/deployment/ {shlex.quote(remote_backend_path)}/deployment/
        fi
        rsync -a --delete --exclude=/deployment/ --exclude=/__init__.py --exclude=/{MANIFEST_NAME} -- \
            "$staging"/{shlex.quote(bundle_dir_name)}/ {shlex.quote(remote_backend_path)}/
        if [ -f "$staging"/{shlex.quote(bundle_dir_name)}/{MANIFEST_NAME} ]; then
            cp -- "$staging"/{shlex.quote(bundle_dir_name)}/{MANIFEST_NAME} {manifest}.tmp
            mv -f -- {manifest}.tmp {manifest}
        fi
        """
        if not system.run_command(command):
            raise RuntimeError(
                f"Failed to install bundle on {system.general_info.hostname}"
            )

    def install_delta(self, system: System, name: str, remote_zip_path: FilePath) -> None:
        """Apply changed files and removals to an installed bundle in a known state."""
        backend = shlex.quote(self._remote_backend(system))
        remote_bundle_dir = posixpath.join(
            system.general_info.blitz_path, self.backend_bundle_path.strip("/")
        )
        source = '"$staging"/' + shlex.quote(name[:-4] if name.endswith(".zip") else name)
        delta = f"{source}/{DELTA_FOLDER}"
        manifest = shlex.quote(posixpath.join(self._remote_backend(system), MANIFEST_NAME))
        command = f"""
        set -e
        staging=$(mktemp -d {shlex.quote(posixpath.join(remote_bundle_dir, '.install.XXXXXX'))})
        trap 'rm -rf -- "$staging"' EXIT
        unzip -o -q {shlex.quote(remote_zip_path)} -d "$staging"
        test -f {delta}/base-manifest.json
        if ! cmp -s {delta}/base-manifest.json {manifest}; then
            echo "Installed bundle changed after comparison; deploy again" >&2
            exit 3
        fi
        # Without a manifest, an interrupted update forces a complete transfer.
        rm -f -- {manifest}
        cd {backend}
        if [ -s {delta}/removed ]; then xargs -0 rm -f -- < {delta}/removed; fi
        if [ -s {delta}/removed-directories ]; then xargs -0 rm -rf -- < {delta}/removed-directories; fi
        # Every staged file is known to differ; never skip one by size and time.
        rsync -a --ignore-times --exclude=/{DELTA_FOLDER}/ --exclude=/{MANIFEST_NAME} -- {source}/ {backend}/
        {self._clear_runtime_caches(system)}
        cp -- {source}/{MANIFEST_NAME} {manifest}.tmp
        mv -f -- {manifest}.tmp {manifest}
        """
        if not system.run_command(command):
            raise RuntimeError(
                f"Failed to install changed files on {system.general_info.hostname}"
            )

    def cleanup_bundle_transfers(self, system: System) -> None:
        """Keep only backend/; transfer archives are not a target-side cache."""
        remote_bundle_dir = posixpath.join(
            system.general_info.blitz_path, self.backend_bundle_path.strip('/')
        )
        command = f"""
        set -e
        for archive in {shlex.quote(remote_bundle_dir)}/*.zip; do
            [ -f "$archive" ] || continue
            rm -rf -- "${{archive%.zip}}"
            rm -f -- "$archive"
        done
        """
        if not system.run_command(command):
            raise RuntimeError(f"Failed to clean bundle transfers on {system.general_info.hostname}")

    def get_bundled_zip(self, system: SystemCatalog) -> tuple[str, FilePath]:
        name = f"{system.to_system_id().to_build_key()}.zip"
        zip_path = FilePath(os.path.join(self.local_bundler_output_path, name))
        return name, zip_path

    @staticmethod
    def _system_label(system: System) -> str:
        return f"{system.general_info.system_name} " f"({system.general_info.hostname})"

    def _apply_system_credentials(self, system: System) -> None:
        if not self.system_host_to_pass_user:
            return

        pass_user = self.system_host_to_pass_user.get(
            system.general_info.hostname,
            self.system_host_to_pass_user.get(system.general_info.system_name),
        )
        if pass_user is None:
            return

        system.password, system.user = pass_user
