from dataclasses import dataclass, field
from enum import Enum
import re
import os
import json
import shlex
from pathlib import Path

from backend.deployment.module.contracts import LaunchSettings, ModuleOutputs, TargetRequirements

from backend.deployment.network_api.utils import FilePath, FolderPath
from backend.deployment.processes import WeightedProcess


class VerificationResult(Enum):
    FATAL = "fatal"
    WARNING = "warning"
    SUCCESS = "success"


def matches_module_type(module: object, *module_types: type) -> bool:
    """Recognize typed modules after watchdog lazy imports reload their classes."""
    identities = {(candidate.__module__, candidate.__qualname__) for candidate in module_types}
    return any(
        (candidate.__module__, candidate.__qualname__) in identities
        for candidate in type(module).__mro__
    )


@dataclass
class Module:
    name: str
    dependencies: tuple[str, ...] = field(default=(), kw_only=True)
    outputs: ModuleOutputs = field(default_factory=ModuleOutputs, kw_only=True)
    targets: TargetRequirements = field(default_factory=TargetRequirements, kw_only=True)

    def get_language_name(self) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} should implement get_language_name()"
        )

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

    launch: LaunchSettings = field(default_factory=LaunchSettings, kw_only=True)

    def get_process_name(self) -> str:
        return self.equivalent_run_definition.get_name() if self.equivalent_run_definition is not None else self.name

    def get_run_argv(self, bundle_path: FolderPath, blitz_path: str | None = None) -> list[str]:
        return shlex.split(self.get_run_command(bundle_path))

    def get_run_directory(self, bundle_path: FolderPath) -> str:
        return str(Path(self.get_project_path(bundle_path)).resolve() / self.launch.working_directory)

    def get_run_environment(self, bundle_path: FolderPath) -> dict[str, str]:
        root = Path(bundle_path).resolve()
        paths = [root / "lib" / self.name]
        module_paths = [root / self.get_language_name() / self.name]
        manifest = root / "runtime-manifest.json"
        if manifest.is_file():
            metadata = json.loads(manifest.read_text())
            if self.name not in metadata["modules"]:
                raise ValueError(f"Module {self.name} is unavailable in this target bundle")
            paths = [root / path for path in metadata["modules"][self.name]["library_paths"]]
            module_paths = [root / path for path in metadata["modules"][self.name].get("module_paths", [])]
        paths.append(root / "deps" / "native")
        environment = dict(self.launch.environment)
        environment.update({
            "LD_LIBRARY_PATH": os.pathsep.join(filter(None, (*[str(path) for path in paths], environment.get("LD_LIBRARY_PATH")))),
            "BLITZ_LIB_DIR": str(root / "lib"),
            "BLITZ_MODULE_PATH": os.pathsep.join(str(path) for path in module_paths),
            "BLITZ_RESOURCE_DIR": str(root / "resources" / self.name),
            "BLITZ_MODULE_DIR": str(root / self.get_language_name() / self.name),
        })
        return environment

    def get_extra_run_argv(self) -> list[str]:
        return [part for key, value in self.extra_run_args for part in (f"--{key}", value)] + list(self.launch.arguments)

    def get_extra_run_args(self) -> str:
        return shlex.join(self.get_extra_run_argv())


@dataclass
class DependencyInstallation:
    def should_rerun_for_each_module(self) -> bool:
        return False

    def verify_dependencies(
        self, requirements_path: FilePath = FilePath("requirements.txt")
    ) -> tuple[VerificationResult, str]:
        return VerificationResult.SUCCESS, ""

    def get_dependency_installation_command(
        self, blitz_path: FolderPath, bundle_path: FolderPath
    ) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} should implement get_dependency_installation_command()"
        )
