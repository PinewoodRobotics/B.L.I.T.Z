import importlib
import pkgutil
import os


def _import_all_modules():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for _, name, _ in pkgutil.iter_modules([current_dir]):
        if name not in ["pipeline", "__init__"]:
            importlib.import_module(f".{name}", package=__package__)


_import_all_modules()
