import re
import shutil
from backend.deployment.compilation.util.systems import (
    Architecture,
    LinuxDistro,
    SystemId,
)
from backend.deployment.compilation_util import CPPBuildConfig, CPPBuildOptions
from backend.deployment.module.base import CompilableModule, Module, VerificationResult
import os

from backend.deployment.module.supported import SupportedModules

orange = "\033[33m"
reset = "\033[0m"


class CodeBundler:
    def __init__(
        self,
        modules: list[Module],
        backend_local_path: str,
        build_folder_path: str,
        output_folder_path: str,
        system_id: SystemId,
        bundle_name: str = "backend_bundle",
    ):
        self.modules: list[Module] = modules
        self.backend_local_path: str = backend_local_path
        self.build_folder_path: str = build_folder_path
        self.output_folder_path: str = output_folder_path
        self.system_id: SystemId = system_id
        self.bundle_name: str = bundle_name + "_" + self.system_id.to_build_key()

    # build/backend_bundle_<system_id>/<language>/<module_name>
    # build/backend_bundle_<system_id>/link/*.so
    def bundle(self) -> str:
        os.makedirs(self.build_folder_path, exist_ok=True)
        os.makedirs(self.output_folder_path, exist_ok=True)

        build_path = os.path.join(self.build_folder_path, self.bundle_name)
        print(f"Bundling {len(self.modules)} modules")
        print()
        for module in self.modules:
            print(f"Verifying module {module.name}...")
            print()

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

            print(f"Assembling module {module.name}...")
            print()
            path = os.path.join(build_path, module.get_language_name(), module.name)
            os.makedirs(path, exist_ok=True)

            module.assemble(path, self.system_id)
            print(f"Module {module.name} assembled successfully")
            print()

            if not isinstance(module, CompilableModule):
                continue

            print(f"Linking module {module.name}...")
            print()
            linking_path = os.path.join(
                build_path, "link", module.get_language_name(), module.name
            )
            os.makedirs(linking_path, exist_ok=True)

            files = self.__get_all_files_matching_pattern(
                path,
                module.get_link_file_pattern(),
            )

            print(f"Copying {len(files)} files to linking path...")
            print()
            for file in files:  # copying here is not ideal but will have to do for now
                _ = shutil.copy(
                    file, os.path.join(linking_path, os.path.basename(file))
                )

        archive_base_path = os.path.join(self.output_folder_path, self.bundle_name)

        print(f"Creating archive {archive_base_path}...")
        print()
        archive_path = shutil.make_archive(
            archive_base_path,
            "zip",
            root_dir=self.build_folder_path,
            base_dir=self.bundle_name,
        )

        return archive_path

    def __get_all_files_matching_pattern(
        self, directory_path: str, pattern: re.Pattern[str]
    ) -> list[str]:
        matched_files: list[str] = []
        for root, _, files in os.walk(directory_path):
            for filename in files:
                if pattern.match(filename):
                    matched_files.append(os.path.join(root, filename))
        return matched_files

    def __question_user(self, question: str) -> bool:
        return input(f"{orange}{question} (y/n): {reset}").lower() == "y"


if __name__ == "__main__":
    bundler = CodeBundler(
        modules=[
            SupportedModules.PythonModule(
                name="example",
                module_folder_path="backend/python/example/",
                extra_run_args=[],
                equivalent_run_definition="example",
            ),
            SupportedModules.RustModule(
                name="test",
                runnable_name="test",
                extra_run_args=[],
                equivalent_run_definition="test",
                project_root_folder_path="backend/rust/test",
            ),
            SupportedModules.CPPLibraryModule(
                name="test",
                project_root_folder_path="backend/cpp/test",
                compilation_config=CPPBuildConfig.with_cmake(
                    clean_build_dir=False,
                    cmake_args=[],
                    compiler_args=[CPPBuildOptions.NONE],
                    libs=[],
                    extra_docker_commands=[],
                ),
            ),
        ],
        backend_local_path="backend/",
        build_folder_path="build/",
        output_folder_path="build/output/",
        bundle_name="backend_bundle",
        system_id=SystemId(
            c_lib_version="2.0.0",
            linux_distro=LinuxDistro.UBUNTU_22,
            architecture=Architecture.AARCH64,
        ),
    )

    archive_path = bundler.bundle()
    print(f"Archive path: {archive_path}")
