"""Resolve module dependencies and target compatibility before any build or transfer."""
from __future__ import annotations

import re
from pathlib import Path
from backend.deployment.compilation.util.systems import SystemId
from backend.deployment.module.base import Module, RunnableModule, matches_module_type


class TargetCompatibilityError(ValueError):
    pass


class ModuleGraph:
    def __init__(self, modules: list[Module]):
        self.modules: dict[str, Module] = {}
        processes: set[str] = set()
        source_folders: dict[Path, str] = {}
        for module in modules:
            if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', module.name):
                raise ValueError(f'Unsafe module ID: {module.name}')
            if module.name in self.modules:
                raise ValueError(f'Duplicate module ID: {module.name}')
            self.modules[module.name] = module
            source = getattr(module, 'module_folder_path', None)
            if source is None:
                source = getattr(module, 'project_root_folder_path', None)
            if source is not None:
                folder = Path(source).resolve()
                if folder in source_folders:
                    raise ValueError(
                        f'One module per source folder: {source_folders[folder]} and '
                        f'{module.name} both use {folder}'
                    )
                source_folders[folder] = module.name
            if matches_module_type(module, RunnableModule):
                process = module.get_process_name()
                if process in processes:
                    raise ValueError(f'Duplicate process ID: {process}')
                processes.add(process)
        self.ordered: list[Module] = []
        visiting: list[str] = []
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise ValueError('Module dependency cycle: ' + ' -> '.join([*visiting, name]))
            if name not in self.modules:
                raise ValueError('Unknown module dependency: ' + ' -> '.join([*visiting, name]))
            if name in visited:
                return
            visiting.append(name)
            for dependency in self.modules[name].dependencies:
                visit(dependency)
            visiting.pop()
            visited.add(name)
            self.ordered.append(self.modules[name])

        for name in self.modules:
            visit(name)

    def closure(self, name: str) -> list[str]:
        result: list[str] = []
        def visit(module_id: str) -> None:
            if module_id in result:
                return
            result.append(module_id)
            for dependency in self.modules[module_id].dependencies:
                visit(dependency)
        visit(name)
        return result

    def reason(self, name: str, system: SystemId) -> str | None:
        def inspect(module_id: str, chain: list[str]) -> str | None:
            reasons = self.modules[module_id].targets.incompatibilities(system)
            if reasons:
                return ' -> '.join([*chain, module_id]) + ': ' + ', '.join(reasons)
            for dependency in self.modules[module_id].dependencies:
                reason = inspect(dependency, [*chain, module_id])
                if reason:
                    return reason
            return None
        return inspect(name, [])

    def compatible(self, system: SystemId) -> list[Module]:
        return [module for module in self.ordered if self.reason(module.name, system) is None]

    def validate_processes(self, process_names: list[str], system: SystemId) -> None:
        runnable = {module.get_process_name(): module for module in self.ordered if matches_module_type(module, RunnableModule)}
        for process in process_names:
            if process not in runnable:
                raise TargetCompatibilityError(f'Unknown assigned process {process}')
            reason = self.reason(runnable[process].name, system)
            if reason:
                raise TargetCompatibilityError(f'Cannot assign {process} to {system.to_build_key()}: {reason}')
