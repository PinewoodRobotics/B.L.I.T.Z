"""Validate the backend source boundary used by public deployment APIs."""
from pathlib import Path

from backend.deployment.module.base import Module
from backend.deployment.module.graph import ModuleGraph


def validate_backend_layout(modules: list[Module], backend_path: str) -> None:
    ModuleGraph(modules)  # Validate folder ownership before any target/build work.
    root = Path(backend_path).resolve()
    for module in modules:
        source = getattr(module, 'module_folder_path', None)
        if source is None:
            source = getattr(module, 'project_root_folder_path', None)
        if source is None:
            raise ValueError(f'Module {module.name} has no source folder')
        path = Path(source).resolve()
        language_root = root / module.get_language_name()
        if path.parent != language_root or path.name == 'common':
            raise ValueError(
                f'Module {module.name} must live in {language_root}/<module>; got {path}. '
                'The common folder is shared source, not a runnable module.'
            )
    # Following symlinks must not pull source from outside the backend boundary.
    for path in root.rglob('*'):
        if path.is_symlink() and not path.resolve().is_relative_to(root):
            raise ValueError(f'Backend source symlink escapes the backend folder: {path}')
