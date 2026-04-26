from dataclasses import dataclass
import os
import posixpath

import shlex
import shutil
from backend.deployment.compilation.cpp.cpp import CPlusPlus
from backend.deployment.compilation.util.commands import run_command
from backend.deployment.compilation.util.cpp_build import CPPBuildConfig
from backend.deployment.compilation.rust.rust import Rust
from backend.deployment.compilation.util.systems import (
    SystemId,
    glibc_to_manylinux_platforms,
)
from backend.deployment.module.base import (
    CompilableModule,
    DependencyInstallation,
    RunnableModule,
    VerificationResult,
)
from backend.deployment.misc import output

VENV_PATH = ".venv/bin/python"


@dataclass
class CPPLibraryModule(CompilableModule):
    compilation_config: CPPBuildConfig

    def get_language_name(self) -> str:
        return "cpp"

    def verify(self) -> tuple[VerificationResult, str]:
        if not os.path.exists(self.project_root_folder_path):
            return (
                VerificationResult.FATAL,
                f"Project root folder path {self.project_root_folder_path} does not exist",
            )

        if not os.path.exists(
            os.path.join(self.project_root_folder_path, "CMakeLists.txt")
        ):
            return (
                VerificationResult.WARNING,
                f"CMakeLists.txt file not found in project root folder path {self.project_root_folder_path}",
            )

        return VerificationResult.SUCCESS, ""

    def assemble(self, result_path: str, system_id: SystemId):
        release_path = CPlusPlus.compile(
            self.name,
            system_id,
            self.compilation_config,
            self.project_root_folder_path,
        )
        _ = shutil.copytree(release_path, result_path, dirs_exist_ok=True)


@dataclass
class CPPRunnableModule(CompilableModule, RunnableModule):
    compilation_config: CPPBuildConfig
    runnable_name: str

    def get_language_name(self) -> str:
        return "cpp"

    def verify(self) -> tuple[VerificationResult, str]:
        if not os.path.exists(self.project_root_folder_path):
            return (
                VerificationResult.FATAL,
                f"Project root folder path {self.project_root_folder_path} does not exist",
            )

        if not os.path.exists(
            os.path.join(self.project_root_folder_path, "CMakeLists.txt")
        ):
            return (
                VerificationResult.WARNING,
                f"CMakeLists.txt file not found in project root folder path {self.project_root_folder_path}",
            )

        return VerificationResult.SUCCESS, ""

    def assemble(self, result_path: str, system_id: SystemId):
        release_path = CPlusPlus.compile(
            self.name,
            system_id,
            self.compilation_config,
            self.project_root_folder_path,
        )
        _ = shutil.copytree(release_path, result_path, dirs_exist_ok=True)

    def get_run_command(self, bundle_path: str) -> str:
        extra_run_args = self.get_extra_run_args()
        return (
            f"{self.get_project_path(bundle_path)}/{self.runnable_name} {extra_run_args}"
        ).strip()


@dataclass
class RustModule(CompilableModule, RunnableModule):
    runnable_name: str

    def get_language_name(self) -> str:
        return "rust"

    def verify(self) -> tuple[VerificationResult, str]:
        if not os.path.exists(self.project_root_folder_path):
            return (
                VerificationResult.FATAL,
                f"Project root folder path {self.project_root_folder_path} does not exist",
            )

        return VerificationResult.SUCCESS, ""

    def assemble(self, result_path: str, system_id: SystemId):
        release_path = Rust.compile(self.name, system_id)
        bin_path = os.path.join(release_path, self.name)
        shutil.copy(bin_path, result_path)

    def get_run_command(self, bundle_path: str) -> str:
        extra_run_args = self.get_extra_run_args()
        return f"{self.get_project_path(bundle_path)}/{self.runnable_name} {extra_run_args}".strip()


@dataclass
class ProtobufModule(CompilableModule):
    def get_language_name(self) -> str:
        return "protobuf"


@dataclass
class ThriftModule(CompilableModule):
    def get_language_name(self) -> str:
        return "thrift"


@dataclass
class PythonModule(RunnableModule, DependencyInstallation):
    module_folder_path: str

    def get_language_name(self) -> str:
        return "python"

    def assemble(self, result_path: str, system_id: SystemId):
        shutil.copytree(self.module_folder_path, result_path, dirs_exist_ok=True)

    def verify_dependencies(
        self, requirements_path: str = "requirements.txt"
    ) -> tuple[VerificationResult, str]:
        if not os.path.exists(requirements_path):
            return (
                VerificationResult.FATAL,
                f"Requirements file {requirements_path} does not exist",
            )

        return VerificationResult.SUCCESS, ""

    def assemble_dependencies(
        self,
        result_path: str,
        system_id: SystemId,
        requirements_path: str = "requirements.txt",
    ) -> None:
        python_version = system_id.python_version
        py_tag = f"{python_version.major}{python_version.minor}"
        abi_tag = f"cp{py_tag}"

        platforms = glibc_to_manylinux_platforms(
            system_id.c_lib_version,
            system_id.architecture,
        )

        cmd = [
            "python",
            "-m",
            "pip",
            "download",
            "--requirement",
            requirements_path,
            "--dest",
            result_path,
            "--only-binary=:all:",
            "--implementation",
            "cp",
            "--python-version",
            py_tag,
            "--abi",
            abi_tag,
        ]

        for platform in platforms:
            cmd.extend(["--platform", platform])

        _ = run_command(
            cmd,
            "Download Python dependencies",
            on_output=output.command_output,
            on_failure=output.command_failure,
        )

    def get_dependency_installation_command(
        self, blitz_path: str, bundle_path: str
    ) -> str:
        venv_python = shlex.quote(posixpath.join(blitz_path, VENV_PATH))
        wheel_dir = shlex.quote(
            posixpath.join(bundle_path, "deps", self.get_language_name())
        )
        return (
            f"cd {shlex.quote(blitz_path)} && "
            f"{venv_python} -m pip install "
            "--no-index "
            "--no-cache-dir "
            f"--find-links {wheel_dir} "
            f"{wheel_dir}/*.whl"
        )

    def get_run_command(self, bundle_path: str) -> str:
        extra_run_args = self.get_extra_run_args()
        return f"{VENV_PATH} -u {self.get_project_path(bundle_path)}/__main__.py {extra_run_args}"

    def verify(self) -> tuple[VerificationResult, str]:
        if not os.path.exists(self.module_folder_path):
            return (
                VerificationResult.FATAL,
                f"Module folder path {self.module_folder_path} does not exist",
            )

        if not os.path.exists(os.path.join(self.module_folder_path, "__main__.py")):
            return (
                VerificationResult.WARNING,
                f"__main__.py file not found in module folder path {self.module_folder_path}",
            )

        return VerificationResult.SUCCESS, ""


class SupportedModules:
    CPPLibraryModule = CPPLibraryModule
    CPPRunnableModule = CPPRunnableModule
    PythonModule = PythonModule
    RustModule = RustModule
    ProtobufModule = ProtobufModule
    ThriftModule = ThriftModule
