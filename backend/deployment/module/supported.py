"""Typed module declarations consumed by the per-system build plan."""

from dataclasses import dataclass
import os
import posixpath
import shlex

from backend.deployment.compilation.util.cpp_build import CPPBuildConfig
from backend.deployment.module.base import (
    CompilableModule,
    DependencyInstallation,
    Module,
    RunnableModule,
    VerificationResult,
)
from backend.deployment.network_api.utils import FilePath, FolderPath

VENV_PATH = FilePath(".venv/bin/python")


@dataclass
class CPPLibraryModule(CompilableModule):
    compilation_config: CPPBuildConfig

    def get_language_name(self) -> str:
        return "cpp"

    def verify(self) -> tuple[VerificationResult, str]:
        if not os.path.exists(self.project_root_folder_path):
            return VerificationResult.FATAL, f"Project root folder path {self.project_root_folder_path} does not exist"
        if not os.path.exists(os.path.join(self.project_root_folder_path, "CMakeLists.txt")):
            return VerificationResult.WARNING, f"CMakeLists.txt file not found in project root folder path {self.project_root_folder_path}"
        return VerificationResult.SUCCESS, ""


@dataclass
class GeneratedModule(CompilableModule):
    def get_language_name(self) -> str:
        return "generated"


@dataclass
class CPPRunnableModule(CompilableModule, RunnableModule):
    compilation_config: CPPBuildConfig
    runnable_name: str

    def get_language_name(self) -> str:
        return "cpp"

    def verify(self) -> tuple[VerificationResult, str]:
        if not os.path.exists(self.project_root_folder_path):
            return VerificationResult.FATAL, f"Project root folder path {self.project_root_folder_path} does not exist"
        if not os.path.exists(os.path.join(self.project_root_folder_path, "CMakeLists.txt")):
            return VerificationResult.WARNING, f"CMakeLists.txt file not found in project root folder path {self.project_root_folder_path}"
        return VerificationResult.SUCCESS, ""

    def get_run_command(self, bundle_path: FolderPath) -> str:
        extra_run_args = self.get_extra_run_args()
        return f"{self.get_project_path(bundle_path)}/{self.runnable_name} {extra_run_args}".strip()


@dataclass
class RustModule(CompilableModule, RunnableModule):
    runnable_name: str

    def get_language_name(self) -> str:
        return "rust"

    def verify(self) -> tuple[VerificationResult, str]:
        if not os.path.exists(self.project_root_folder_path):
            return VerificationResult.FATAL, f"Project root folder path {self.project_root_folder_path} does not exist"
        return VerificationResult.SUCCESS, ""

    def get_run_command(self, bundle_path: FolderPath) -> str:
        extra_run_args = self.get_extra_run_args()
        return f"{self.get_project_path(bundle_path)}/{self.runnable_name} {extra_run_args}".strip()


@dataclass
class RustLibraryModule(CompilableModule):
    def get_language_name(self) -> str:
        return "rust"

    def verify(self) -> tuple[VerificationResult, str]:
        if not os.path.isfile(os.path.join(self.project_root_folder_path, "Cargo.toml")):
            return VerificationResult.FATAL, f"Cargo.toml not found in {self.project_root_folder_path}"
        return VerificationResult.SUCCESS, ""


@dataclass
class PythonModule(RunnableModule, DependencyInstallation):
    module_folder_path: FolderPath

    def get_language_name(self) -> str:
        return "python"

    def verify_dependencies(
        self, requirements_path: FilePath = FilePath("requirements.txt")
    ) -> tuple[VerificationResult, str]:
        if not os.path.exists(requirements_path):
            return VerificationResult.FATAL, f"Requirements file {requirements_path} does not exist"
        return VerificationResult.SUCCESS, ""

    def get_dependency_installation_command(
        self, blitz_path: FolderPath, bundle_path: FolderPath
    ) -> str:
        venv_python = shlex.quote(posixpath.join(blitz_path, VENV_PATH))
        deps_dir = posixpath.join(bundle_path, "deps", self.get_language_name())
        quoted_deps_dir = shlex.quote(deps_dir)
        requirements_path = shlex.quote(posixpath.join(deps_dir, "requirements.txt"))
        return (
            f"cd {shlex.quote(blitz_path)} && "
            f"{venv_python} -m pip install --no-index --no-cache-dir "
            f"--find-links {quoted_deps_dir} --requirement {requirements_path}"
        )

    def get_run_command(self, bundle_path: FolderPath) -> str:
        extra_run_args = self.get_extra_run_args()
        return f"{VENV_PATH} -u {self.get_project_path(bundle_path)}/__main__.py {extra_run_args}"

    def verify(self) -> tuple[VerificationResult, str]:
        if not os.path.exists(self.module_folder_path):
            return VerificationResult.FATAL, f"Module folder path {self.module_folder_path} does not exist"
        if not os.path.exists(os.path.join(self.module_folder_path, "__main__.py")):
            return VerificationResult.WARNING, f"__main__.py file not found in module folder path {self.module_folder_path}"
        return VerificationResult.SUCCESS, ""


class SupportedModules:
    CPPLibraryModule = CPPLibraryModule
    CPPRunnableModule = CPPRunnableModule
    PythonModule = PythonModule
    RustModule = RustModule
    RustLibraryModule = RustLibraryModule
    GeneratedModule = GeneratedModule

    _Generic = Module
