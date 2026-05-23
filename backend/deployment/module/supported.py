from dataclasses import dataclass
import os
import posixpath

import shlex
import shutil
import subprocess
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
    Module,
    RunnableModule,
    VerificationResult,
)
from backend.deployment.network_api.utils import FilePath, FolderPath

VENV_PATH = FilePath(".venv/bin/python")
PYTHON_BUILD_REQUIREMENTS = ("setuptools", "wheel")


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

    def assemble(self, result_path: FolderPath, system_id: SystemId):
        release_path = CPlusPlus.compile(
            self.name,
            system_id,
            self.compilation_config,
            self.project_root_folder_path,
        )
        _ = shutil.copytree(release_path, result_path, dirs_exist_ok=True)


@dataclass
class GeneratedModule(CompilableModule):
    def get_language_name(self) -> str:
        return "generated"

    def assemble(self, result_path: FolderPath, system_id: SystemId):
        parent_dir = FolderPath(os.path.dirname(result_path))
        shutil.copytree(self.project_root_folder_path, parent_dir, dirs_exist_ok=True)


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

    def assemble(self, result_path: FolderPath, system_id: SystemId):
        release_path = CPlusPlus.compile(
            self.name,
            system_id,
            self.compilation_config,
            self.project_root_folder_path,
        )
        _ = shutil.copytree(release_path, result_path, dirs_exist_ok=True)

    def get_run_command(self, bundle_path: FolderPath) -> str:
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

    def assemble(self, result_path: FolderPath, system_id: SystemId):
        release_path = Rust.compile(self.name, system_id)
        bin_path = FilePath(os.path.join(release_path, self.name))
        shutil.copy(bin_path, result_path)

    def get_run_command(self, bundle_path: FolderPath) -> str:
        extra_run_args = self.get_extra_run_args()
        return (
            f"{self.get_project_path(bundle_path)}/{self.runnable_name} {extra_run_args}"
        ).strip()


@dataclass
class PythonModule(RunnableModule, DependencyInstallation):
    module_folder_path: FolderPath

    def get_language_name(self) -> str:
        return "python"

    def assemble(self, result_path: FolderPath, system_id: SystemId):
        shutil.copytree(self.module_folder_path, result_path, dirs_exist_ok=True)

    def verify_dependencies(
        self, requirements_path: FilePath = FilePath("requirements.txt")
    ) -> tuple[VerificationResult, str]:
        if not os.path.exists(requirements_path):
            return (
                VerificationResult.FATAL,
                f"Requirements file {requirements_path} does not exist",
            )

        return VerificationResult.SUCCESS, ""

    def assemble_dependencies(
        self,
        result_path: FolderPath,
        system_id: SystemId,
        requirements_path: FilePath = FilePath("requirements.txt"),
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

        try:
            _ = run_command(
                cmd,
                "Download Python binary dependencies",
                on_failure=lambda _label, _tail: None,
            )
        except subprocess.CalledProcessError:
            # Wheel-only cross-downloads fail when any requirement lacks a
            # compatible target wheel. Classify requirements individually so
            # source archives are fetched only for packages that must build on
            # the target.
            print(
                "Some Python dependencies do not have target wheels; "
                "checking requirements individually."
            )
            self._download_mixed_binary_and_source_dependencies(
                result_path,
                requirements_path,
                platforms,
                py_tag,
                abi_tag,
            )

        self._download_build_requirements(result_path)
        shutil.copy(requirements_path, os.path.join(result_path, "requirements.txt"))

    def _download_mixed_binary_and_source_dependencies(
        self,
        result_path: FolderPath,
        requirements_path: FilePath,
        platforms: list[str],
        py_tag: str,
        abi_tag: str,
    ) -> None:
        # First try each top-level requirement as a target-compatible wheel. Only
        # requirements that fail that probe are sent to the source download pass,
        # preventing wheel-capable packages from being bundled for manual builds.
        index_args, requirements = self._read_downloadable_requirements(
            requirements_path
        )
        source_requirements: list[str] = []
        for requirement in requirements:
            if not self._download_binary_requirement(
                result_path,
                requirement,
                index_args,
                platforms,
                py_tag,
                abi_tag,
            ):
                print(
                    f"No compatible target wheel for {requirement}; "
                    "will bundle source archive."
                )
                source_requirements.append(requirement)
            else:
                print(f"Bundled target wheel for {requirement}.")

        if source_requirements:
            self._download_source_requirements(
                result_path,
                index_args,
                source_requirements,
            )

    def _download_binary_requirement(
        self,
        result_path: FolderPath,
        requirement: str,
        index_args: list[str],
        platforms: list[str],
        py_tag: str,
        abi_tag: str,
    ) -> bool:
        # This is the same target-wheel constraint as the original bulk command,
        # but scoped to one top-level requirement so a single missing wheel does
        # not force the whole requirements file down the source path.
        cmd = [
            "python",
            "-m",
            "pip",
            "download",
            *index_args,
            requirement,
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

        return (
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            ).returncode
            == 0
        )

    def _download_source_requirements(
        self,
        result_path: FolderPath,
        index_args: list[str],
        requirements: list[str],
    ) -> None:
        # Download source distributions only for top-level requirements that did
        # not have target wheels. --no-deps is deliberate: dependencies should
        # come from the wheel pass or be listed explicitly in requirements.txt,
        # instead of forcing local source metadata/build probes for transitive
        # packages such as scipy.
        for requirement in requirements:
            print(f"Downloading source archive for {requirement}.")
            _ = run_command(
                [
                    "python",
                    "-m",
                    "pip",
                    "download",
                    *index_args,
                    requirement,
                    "--dest",
                    result_path,
                    "--no-binary=:all:",
                    "--no-deps",
                ],
                f"Download Python source dependency {requirement}",
            )

    def _read_downloadable_requirements(
        self, requirements_path: FilePath
    ) -> tuple[list[str], list[str]]:
        # Extract package requirement lines for per-package wheel probes, while
        # preserving simple index options such as --find-links so package-specific
        # sources in requirements.txt are still considered.
        index_args: list[str] = []
        requirements: list[str] = []
        with open(requirements_path) as requirements_file:
            for raw_line in requirements_file:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith(("--find-links", "-f ")):
                    index_args.extend(shlex.split(line))
                    continue
                if line.startswith(("--index-url", "-i ", "--extra-index-url")):
                    index_args.extend(shlex.split(line))
                    continue
                if line.startswith("--trusted-host"):
                    index_args.extend(shlex.split(line))
                    continue
                if line.startswith("-"):
                    continue

                requirement, _, _comment = line.partition(" #")
                requirements.append(requirement.strip())

        return index_args, requirements

    def _download_build_requirements(self, result_path: FolderPath) -> None:
        # Seed the offline directory with common PEP 517/build-backend tools so
        # target-side source builds can create wheels without reaching PyPI.
        _ = run_command(
            [
                "python",
                "-m",
                "pip",
                "download",
                "--dest",
                result_path,
                "--only-binary=:all:",
                *PYTHON_BUILD_REQUIREMENTS,
            ],
            "Download Python build requirements",
        )

    def get_dependency_installation_command(
        self, blitz_path: FolderPath, bundle_path: FolderPath
    ) -> str:
        venv_python = shlex.quote(posixpath.join(blitz_path, VENV_PATH))
        deps_dir = posixpath.join(bundle_path, "deps", self.get_language_name())
        quoted_deps_dir = shlex.quote(deps_dir)
        requirements_path = shlex.quote(posixpath.join(deps_dir, "requirements.txt"))
        # Install from requirements.txt against the bundled find-links directory.
        # This lets pip choose bundled wheels when present and build bundled
        # source archives on the target when no wheel exists.
        return (
            f"cd {shlex.quote(blitz_path)} && "
            f"{venv_python} -m pip install "
            "--no-index "
            "--no-cache-dir "
            f"--find-links {quoted_deps_dir} "
            f"--requirement {requirements_path}"
        )

    def get_run_command(self, bundle_path: FolderPath) -> str:
        extra_run_args = self.get_extra_run_args()
        return (
            f"{VENV_PATH} -u "
            f"{self.get_project_path(bundle_path)}/__main__.py {extra_run_args}"
        )

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
    GeneratedModule = GeneratedModule

    _Generic = Module
