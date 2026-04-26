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
from backend.deployment.compilation.util.cpp_build import (
    CPPBuildConfig,
    CPPBuildOptions,
)
from backend.deployment.module.base import (
    CompilableModule,
    DependencyInstallation,
    Module,
    VerificationResult,
)
import os

from backend.deployment.misc import output
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
        bundle_name: str = "backend-bundle",
        bundle_dependencies: bool = False,
        additional_files: list[str] | None = None,
    ):
        self.modules: list[Module] = modules
        self.backend_local_path: str = backend_local_path
        self.build_folder_path: str = build_folder_path
        self.output_folder_path: str = output_folder_path
        self.system_id: SystemId = system_id
        self.bundle_name: str = bundle_name
        self.full_bundle_name: str = f"{bundle_name}-{self.system_id.to_build_key()}"
        self.bundle_dependencies: bool = bundle_dependencies
        self.additional_files: set[str] = {backend_local_path + "deploy.py"} | set(
            additional_files or []
        )
        self.installed_deps_lang_names: set[str] = set()

    # build/backend-bundle/backend-bundle-<system_id>/<language>/<module_name>
    # build/backend-bundle/backend-bundle-<system_id>/link/*.so
    def bundle(self) -> str:
        os.makedirs(self.build_folder_path, exist_ok=True)
        os.makedirs(self.output_folder_path, exist_ok=True)

        bundle_root_path = os.path.join(self.build_folder_path, self.bundle_name)
        os.makedirs(bundle_root_path, exist_ok=True)

        build_path = os.path.join(bundle_root_path, self.full_bundle_name)
        if os.path.exists(build_path):
            if os.path.isdir(build_path):
                shutil.rmtree(build_path)
            else:
                os.unlink(build_path)
        os.makedirs(build_path, exist_ok=True)

        output.start_bundle(
            self.full_bundle_name,
            self.system_id.to_build_key(),
            [
                f"{module.name} ({module.get_language_name()})"
                for module in self.modules
            ],
            build_path,
        )

        for module_index, module in enumerate(self.modules, start=1):
            build_output_path = os.path.join(
                build_path, module.get_language_name(), module.name
            )
            os.makedirs(build_output_path, exist_ok=True)

            deps_output_path = os.path.join(
                build_path, "deps", module.get_language_name()
            )
            os.makedirs(deps_output_path, exist_ok=True)

            self.verify_module(module, module_index)
            self.assemble_module(module, build_output_path)

            if isinstance(module, CompilableModule):
                self.link_module(module, build_path)
                output.complete_module("assembled")

            if (
                self.bundle_dependencies
                and isinstance(module, DependencyInstallation)
                and (
                    module.get_language_name() not in self.installed_deps_lang_names
                    or module.should_rerun_for_each_module()
                )
            ):
                self.assemble_dependencies(module, deps_output_path)
                self.installed_deps_lang_names.add(module.get_language_name())

        for additional_file in self.additional_files:
            _ = shutil.copy(
                additional_file,
                build_path,
            )

        archive_base_path = os.path.join(self.output_folder_path, self.full_bundle_name)

        output.start_archive(archive_base_path)
        archive_path = shutil.make_archive(
            archive_base_path,
            "zip",
            root_dir=bundle_root_path,
            base_dir=self.full_bundle_name,
        )
        output.finish_bundle(archive_path)

        return archive_path

    def assemble_dependencies(
        self, module: DependencyInstallation, deps_output_path: str
    ):
        output.step("Assemble dependencies")
        output.detail("destination", deps_output_path)
        module.assemble_dependencies(deps_output_path, self.system_id)
        output.success("Assembly complete")

    def verify_module(self, module: Module, module_index: int):
        output.start_module(
            module_index,
            len(self.modules),
            module.name,
            module.get_language_name(),
        )
        output.step("Verify module")

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

        output.success("Verification passed")

    def assemble_module(self, module: Module, build_output_path: str):
        output.step("Assemble module")
        output.detail("destination", build_output_path)
        module.assemble(build_output_path, self.system_id)
        output.success("Assembly complete")

    def link_module(self, module: CompilableModule, build_output_path: str):
        linking_path = os.path.join(
            build_output_path, "link", module.get_language_name(), module.name
        )
        os.makedirs(linking_path, exist_ok=True)

        output.step("Collect linkable artifacts")
        output.detail("destination", linking_path)
        files = self.__get_all_files_matching_pattern(
            build_output_path,
            module.get_link_file_pattern(),
        )

        output.detail("matched files", len(files))
        for file in files:  # copying here is not ideal but will have to do for now
            _ = shutil.copy(file, os.path.join(linking_path, os.path.basename(file)))
        output.success("Link artifacts copied")
        output.complete_module("assembled")

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
        bundle_name="backend-bundle",
        system_id=SystemId(
            c_lib_version="2.39",
            linux_distro=LinuxDistro.UBUNTU_22,
            architecture=Architecture.AARCH64,
            python_version=PythonVersion(major=3, minor=12),
        ),
        bundle_dependencies=False,
        additional_files=["backend/deploy.py"],
    )

    _ = bundler.bundle()
