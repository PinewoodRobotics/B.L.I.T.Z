"""Typed module declarations consumed by the per-system build plan."""

from dataclasses import dataclass, field
from pathlib import Path
from backend.deployment.module.contracts import PythonEntrypoint, relative_path
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

    def get_run_argv(self, bundle_path: FolderPath, blitz_path: str | None = None) -> list[str]:
        executable = Path(self.get_project_path(bundle_path)).resolve() / relative_path(self.runnable_name)
        return [str(executable), *self.get_extra_run_argv()]

    def get_run_command(self, bundle_path: FolderPath) -> str:
        return shlex.join(self.get_run_argv(bundle_path))


@dataclass
class RustModule(CompilableModule, RunnableModule):
    runnable_name: str

    def get_language_name(self) -> str:
        return "rust"

    def verify(self) -> tuple[VerificationResult, str]:
        if not os.path.exists(self.project_root_folder_path):
            return VerificationResult.FATAL, f"Project root folder path {self.project_root_folder_path} does not exist"
        return VerificationResult.SUCCESS, ""

    def get_run_argv(self, bundle_path: FolderPath, blitz_path: str | None = None) -> list[str]:
        executable = Path(self.get_project_path(bundle_path)).resolve() / relative_path(self.runnable_name)
        return [str(executable), *self.get_extra_run_argv()]

    def get_run_command(self, bundle_path: FolderPath) -> str:
        return shlex.join(self.get_run_argv(bundle_path))


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
    entrypoint: PythonEntrypoint = field(default_factory=PythonEntrypoint, kw_only=True)

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

    def get_run_environment(self, bundle_path: FolderPath) -> dict[str, str]:
        environment = super().get_run_environment(bundle_path)
        project = str(Path(self.get_project_path(bundle_path)).resolve())
        # Sibling module source is not an import API. Shared Python code is
        # staged as this module's common package; native libraries remain scoped.
        shared = str(Path(bundle_path).resolve() / 'shared')
        environment["PYTHONPATH"] = os.pathsep.join(filter(None, (project, shared, environment["LD_LIBRARY_PATH"], environment.get("PYTHONPATH"))))
        return environment

    def get_run_argv(self, bundle_path: FolderPath, blitz_path: str | None = None) -> list[str]:
        root = Path(bundle_path).resolve()
        interpreter = Path(blitz_path).resolve() / VENV_PATH if blitz_path else root.parent / VENV_PATH
        project = Path(self.get_project_path(bundle_path)).resolve()
        entry = ["-m", self.entrypoint.package] if self.entrypoint.package else [str(project / self.entrypoint.file)]
        return [str(interpreter), "-u", *entry, *self.get_extra_run_argv()]

    def get_run_command(self, bundle_path: FolderPath) -> str:
        return shlex.join(self.get_run_argv(bundle_path))

    def verify(self) -> tuple[VerificationResult, str]:
        if not os.path.isdir(self.module_folder_path):
            return VerificationResult.FATAL, f"Module folder path {self.module_folder_path} does not exist"
        if self.entrypoint.file and not os.path.isfile(os.path.join(self.module_folder_path, self.entrypoint.file)):
            return VerificationResult.FATAL, f"Python entrypoint {self.entrypoint.file} not found in {self.module_folder_path}"
        if self.entrypoint.package:
            package = Path(self.module_folder_path).joinpath(*self.entrypoint.package.split("."))
            if not package.with_suffix(".py").is_file() and not (package / "__main__.py").is_file():
                return VerificationResult.FATAL, f"Runnable Python package {self.entrypoint.package} not found"
        return VerificationResult.SUCCESS, ""


class SupportedModules:
    CPPLibraryModule = CPPLibraryModule
    CPPRunnableModule = CPPRunnableModule
    PythonModule = PythonModule
    RustModule = RustModule
    RustLibraryModule = RustLibraryModule
    GeneratedModule = GeneratedModule

    _Generic = Module
