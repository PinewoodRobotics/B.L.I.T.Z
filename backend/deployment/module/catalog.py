"""Declare modules by folder name relative to the deployment file."""
from pathlib import Path
import re

from backend.deployment.compilation.util.cpp_build import CPPBuildConfig
from backend.deployment.module.contracts import LaunchSettings, ModuleOutputs, PythonEntrypoint, TargetRequirements
from backend.deployment.module.supported import CPPLibraryModule, CPPRunnableModule, PythonModule, RustLibraryModule, RustModule
from backend.deployment.network_api.utils import FolderPath
from backend.deployment.processes import WeightedProcess


class BackendModules:
    """Use BackendModules(__file__) in deploy.py; no paths depend on cwd.

    Names select backend/<language>/<name>. Common is shared source rather than
    a module. New convenience declarations run ordinary programs without BLITZ
    CLI flags; legacy programs can explicitly opt in through LaunchSettings.
    """

    def __init__(self, deploy_file: str | Path):
        self.backend_path = FolderPath(str(Path(deploy_file).resolve().parent))

    def _source(self, language: str, name: str) -> FolderPath:
        if name == 'common' or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', name):
            raise ValueError(f'Expected a module folder name, got {name!r}')
        return FolderPath(str(Path(self.backend_path) / language / name))

    def python(
        self, name: str, *, process: WeightedProcess,
        entrypoint: str | PythonEntrypoint = '__main__.py',
        dependencies: tuple[str, ...] = (), outputs: ModuleOutputs = ModuleOutputs(),
        targets: TargetRequirements = TargetRequirements(),
        launch: LaunchSettings = LaunchSettings(accepts_blitz_flags=False),
    ) -> PythonModule:
        return PythonModule(
            name, [], process, self._source('python', name),
            entrypoint=PythonEntrypoint(file=entrypoint) if isinstance(entrypoint, str) else entrypoint,
            dependencies=dependencies, outputs=outputs, targets=targets, launch=launch,
        )

    def cpp_library(
        self, name: str, *, compilation: CPPBuildConfig | None = None,
        dependencies: tuple[str, ...] = (), outputs: ModuleOutputs = ModuleOutputs(),
        targets: TargetRequirements = TargetRequirements(),
    ) -> CPPLibraryModule:
        return CPPLibraryModule(
            name, self._source('cpp', name), compilation or CPPBuildConfig.with_cmake(),
            dependencies=dependencies, outputs=outputs, targets=targets,
        )

    def cpp(
        self, name: str, *, process: WeightedProcess, executable: str | None = None,
        compilation: CPPBuildConfig | None = None,
        dependencies: tuple[str, ...] = (), outputs: ModuleOutputs = ModuleOutputs(),
        targets: TargetRequirements = TargetRequirements(),
        launch: LaunchSettings = LaunchSettings(accepts_blitz_flags=False),
    ) -> CPPRunnableModule:
        return CPPRunnableModule(
            name, [], process, self._source('cpp', name),
            compilation or CPPBuildConfig.with_cmake(), executable or name,
            dependencies=dependencies, outputs=outputs, targets=targets, launch=launch,
        )

    def rust_library(
        self, name: str, *, dependencies: tuple[str, ...] = (),
        outputs: ModuleOutputs = ModuleOutputs(), targets: TargetRequirements = TargetRequirements(),
    ) -> RustLibraryModule:
        return RustLibraryModule(
            name, self._source('rust', name), dependencies=dependencies,
            outputs=outputs, targets=targets,
        )

    def rust(
        self, name: str, *, process: WeightedProcess, executable: str | None = None,
        dependencies: tuple[str, ...] = (), outputs: ModuleOutputs = ModuleOutputs(),
        targets: TargetRequirements = TargetRequirements(),
        launch: LaunchSettings = LaunchSettings(accepts_blitz_flags=False),
    ) -> RustModule:
        return RustModule(
            name, [], process, self._source('rust', name), executable or name,
            dependencies=dependencies, outputs=outputs, targets=targets, launch=launch,
        )
