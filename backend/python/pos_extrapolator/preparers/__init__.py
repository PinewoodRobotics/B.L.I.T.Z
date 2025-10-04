import os
import importlib
from pathlib import Path


def _discover_and_import_modules():
    current_dir = Path(__file__).parent

    for file_path in current_dir.glob("*.py"):
        if file_path.name == "__init__.py":
            continue

        module_name = file_path.stem
        module_path = f"{__name__}.{module_name}"

        try:
            importlib.import_module(module_path)
        except ImportError as e:
            print(f"Failed to import {module_path}: {e}")


_discover_and_import_modules()
