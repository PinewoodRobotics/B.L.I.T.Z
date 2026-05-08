import os
import posixpath
import shlex

from backend.deployment.module.base import DependencyInstallation, Module
from backend.deployment.network_api.system_api import System
from backend.deployment.network_api.utils import FilePath, FolderPath
from backend.deployment.network_api.zeroconf import (
    DiscoveredNetworkSystem,
)


class Rsyncer:
    def __init__(
        self,
        modules: list[Module],
        local_bundler_output_path: FolderPath,
        backend_bundle_path: FolderPath,
        systems: set[System],
        are_deps_bundled: bool = False,
        system_host_to_pass_user: dict[str, tuple[str, str]] | None = None,
    ):
        self.modules: list[Module] = modules
        self.local_bundler_output_path: FolderPath = local_bundler_output_path
        self.backend_bundle_path: FolderPath = backend_bundle_path
        self.systems: set[System] = systems
        self.system_host_to_pass_user: dict[str, tuple[str, str]] | None = (
            system_host_to_pass_user
        )
        self.are_deps_bundled: bool = are_deps_bundled

    def deploy(self) -> None:
        for system in sorted(self.systems, key=self._system_label):
            self._apply_system_credentials(system)
            name, remote_zip_path = self.rsync_bundle_zip(system)
            self.install_bundle(system, name, FilePath(remote_zip_path))

            if self.are_deps_bundled:
                self.install_dependencies(system)

    def install_dependencies(self, system: System) -> None:
        installed_deps_lang_names: set[str] = set()
        for module in self.modules:
            if not isinstance(module, DependencyInstallation):
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

    def rsync_bundle_zip(self, system: System) -> tuple[str, FilePath]:
        name, zip_path = self.get_bundled_zip(system.general_info)
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
        remote_extracted_bundle_path = FolderPath(
            posixpath.join(remote_bundle_dir, bundle_dir_name)
        )

        command = f"""
        rm -rf {shlex.quote(remote_extracted_bundle_path)} &&
        unzip -o {shlex.quote(remote_zip_path)} -d {shlex.quote(remote_bundle_dir)} &&
        rsync -a {shlex.quote(remote_extracted_bundle_path)}/ {shlex.quote(remote_backend_path)}/ &&
        rm -rf {shlex.quote(remote_extracted_bundle_path)}
        """
        if not system.run_command(command):
            raise RuntimeError(
                f"Failed to extract bundle on {system.general_info.hostname}"
            )

    def get_bundled_zip(self, system: DiscoveredNetworkSystem) -> tuple[str, FilePath]:
        name = f"backend-bundle-{system.to_system_id().to_build_key()}.zip"
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
