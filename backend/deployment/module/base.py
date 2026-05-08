from dataclasses import dataclass
from enum import Enum
import re
import os

from backend.deployment.compilation.util.systems import SystemId
from backend.deployment.network_api.utils import FilePath, FolderPath
from backend.deployment.processes import WeightedProcess


class VerificationResult(Enum):
    FATAL = "fatal"
    WARNING = "warning"
    SUCCESS = "success"


@dataclass
class Module:
    name: str

    def get_language_name(self) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} should implement get_language_name()"
        )

    def assemble(self, _result_path: FolderPath, _system_id: SystemId) -> None:
        raise NotImplementedError(f"{type(self).__name__} should implement assemble()")

    def verify(self) -> tuple[VerificationResult, str]:
        return VerificationResult.SUCCESS, ""

    def get_project_path(self, bundle_path: FolderPath) -> FolderPath:
        return FolderPath(
            os.path.join(bundle_path, self.get_language_name(), self.name)
        )


@dataclass
class CompilableModule(Module):
    project_root_folder_path: FolderPath

    def additional_link_file_extensions(self) -> list[str]:
        return []

    def get_link_file_pattern(self) -> re.Pattern[str]:
        default_extensions = ["so", "dylib", "dll", "a", "lib"]
        extensions = default_extensions + self.additional_link_file_extensions()
        extension_pattern = "|".join(
            re.escape(extension.lstrip(".")) for extension in extensions
        )
        return re.compile(rf".*\.({extension_pattern})(\.\d+)*$")


@dataclass
class RunnableModule(Module):
    extra_run_args: list[tuple[str, str]]
    equivalent_run_definition: WeightedProcess

    def get_run_command(self, _bundle_path: FolderPath) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} should implement get_run_command(bundle_path)"
        )

    def get_extra_run_args(self) -> str:
        return (
            " ".join([f"--{arg[0]} {arg[1]}" for arg in self.extra_run_args])
            if self.extra_run_args
            else ""
        )


@dataclass
class DependencyInstallation:
    def should_rerun_for_each_module(self) -> bool:
        return False

    def verify_dependencies(
        self, requirements_path: FilePath = FilePath("requirements.txt")
    ) -> tuple[VerificationResult, str]:
        return VerificationResult.SUCCESS, ""

    def assemble_dependencies(
        self,
        result_path: FolderPath,
        system_id: SystemId,
        requirements_path: FilePath = FilePath("requirements.txt"),
    ) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} should implement assemble_dependencies()"
        )

    def get_dependency_installation_command(
        self, blitz_path: FolderPath, bundle_path: FolderPath
    ) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} should implement get_dependency_installation_command()"
        )
