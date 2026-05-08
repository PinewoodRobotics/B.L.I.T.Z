if __name__ == "__main__" and __package__ is None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import re
import shutil
from backend.deployment.compilation.util.systems import (
    Architecture,
    LinuxDistro,
    SystemId,
    PythonVersion,
)
from backend.deployment.module.base import (
    CompilableModule,
    DependencyInstallation,
    Module,
    VerificationResult,
)
import os

from backend.deployment.network_api.utils import FilePath, FolderPath


class CodeBundler:
    def __init__(
        self,
        modules: list[Module],
        backend_local_path: FolderPath,
        build_folder_path: FolderPath,
        output_folder_path: FolderPath,
        system_id: SystemId,
        bundle_name: str = "backend-bundle",
        bundle_dependencies: bool = False,
        additional_files: list[FilePath] | None = None,
    ):
        self.modules: list[Module] = modules
        self.backend_local_path: FolderPath = backend_local_path
        self.build_folder_path: FolderPath = build_folder_path
        self.output_folder_path: FolderPath = output_folder_path
        self.system_id: SystemId = system_id
        self.bundle_name: str = bundle_name
        self.full_bundle_name: str = f"{bundle_name}-{self.system_id.to_build_key()}"
        self.bundle_dependencies: bool = bundle_dependencies
        self.additional_files: set[FilePath] = {
            FilePath(os.path.join(backend_local_path, "deploy.py"))
        } | set(additional_files or [])
        self.installed_deps_lang_names: set[str] = set()

    # build/backend-bundle/backend-bundle-<system_id>/<language>/<module_name>
    # build/backend-bundle/backend-bundle-<system_id>/link/*.so
    def bundle(self) -> FilePath:
        os.makedirs(self.build_folder_path, exist_ok=True)
        os.makedirs(self.output_folder_path, exist_ok=True)

        bundle_root_path = FolderPath(
            os.path.join(self.build_folder_path, self.bundle_name)
        )
        os.makedirs(bundle_root_path, exist_ok=True)

        build_path = FolderPath(os.path.join(bundle_root_path, self.full_bundle_name))
        if os.path.exists(build_path):
            if os.path.isdir(build_path):
                shutil.rmtree(build_path)
            else:
                os.unlink(build_path)
        os.makedirs(build_path, exist_ok=True)

        for module in self.modules:
            build_output_path = FolderPath(
                os.path.join(build_path, module.get_language_name(), module.name)
            )
            os.makedirs(build_output_path, exist_ok=True)

            deps_output_path = FolderPath(
                os.path.join(build_path, "deps", module.get_language_name())
            )
            os.makedirs(deps_output_path, exist_ok=True)

            self.verify_module(module)
            module.assemble(build_output_path, self.system_id)

            if isinstance(module, CompilableModule):
                self.link_module(module, build_path)

            if (
                self.bundle_dependencies
                and isinstance(module, DependencyInstallation)
                and (
                    module.get_language_name() not in self.installed_deps_lang_names
                    or module.should_rerun_for_each_module()
                )
            ):
                module.assemble_dependencies(deps_output_path, self.system_id)
                self.installed_deps_lang_names.add(module.get_language_name())

        for additional_file in self.additional_files:
            _ = shutil.copy(
                additional_file,
                build_path,
            )

        archive_base_path = FilePath(
            os.path.join(self.output_folder_path, self.full_bundle_name)
        )

        archive_path = shutil.make_archive(
            archive_base_path,
            "zip",
            root_dir=bundle_root_path,
            base_dir=self.full_bundle_name,
        )

        return FilePath(archive_path)

    def verify_module(self, module: Module):
        success, error_message = module.verify()
        if success == VerificationResult.FATAL:
            raise Exception(
                f"Module {module.name} verification failed: {error_message}"
            )

        if success == VerificationResult.WARNING and not self.__question_user(
            f"Module {module.name} verification failed: {error_message}. Continue anyway?"
        ):
            raise Exception(
                f"Module {module.name} verification failed: {error_message}"
            )

    def link_module(self, module: CompilableModule, build_output_path: FolderPath):
        linking_path = FolderPath(
            os.path.join(
                build_output_path,
                "link",
                module.get_language_name(),
                module.name,
            )
        )
        os.makedirs(linking_path, exist_ok=True)

        files = self.__get_all_files_matching_pattern(
            build_output_path,
            module.get_link_file_pattern(),
        )

        for file in files:  # copying here is not ideal but will have to do for now
            _ = shutil.copy(file, os.path.join(linking_path, os.path.basename(file)))

    def __get_all_files_matching_pattern(
        self, directory_path: FolderPath, pattern: re.Pattern[str]
    ) -> list[FilePath]:
        matched_files: list[FilePath] = []
        for root, _, files in os.walk(directory_path):
            for filename in files:
                if pattern.match(filename):
                    matched_files.append(FilePath(os.path.join(root, filename)))
        return matched_files

    def __question_user(self, question: str) -> bool:
        return input(f"{question} (y/n): ").lower() == "y"


if __name__ == "__main__":
    bundler = CodeBundler(
        modules=[],
        backend_local_path=FolderPath("backend/"),
        build_folder_path=FolderPath("build/"),
        output_folder_path=FolderPath("build/output/"),
        bundle_name="backend-bundle",
        system_id=SystemId(
            c_lib_version="2.39",
            linux_distro=LinuxDistro.JETPACK_L4T_R36_2,
            architecture=Architecture.AARCH64,
            python_version=PythonVersion(major=3, minor=12),
        ),
        bundle_dependencies=False,
        additional_files=[FilePath("backend/deploy.py")],
    )

    _ = bundler.bundle()
