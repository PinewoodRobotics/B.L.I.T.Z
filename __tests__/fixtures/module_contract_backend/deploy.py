"""Self-contained dependency graph, colliding sonames, and two Python entrypoints."""
from pathlib import Path
from backend.deployment.compilation.util.cpp_build import CPPBuildConfig
from backend.deployment.module.base import Module
from backend.deployment.module.contracts import LaunchSettings, ModuleOutputs, PythonEntrypoint
from backend.deployment.module.supported import CPPLibraryModule, CPPRunnableModule, PythonModule
from backend.deployment.network_api.utils import FolderPath
from backend.deployment.processes import WeightedProcess

ROOT = Path(__file__).resolve().parent

class Processes(WeightedProcess):
    NATIVE = 'native-process', 1.0
    FIRST = 'python-first', 1.0
    SECOND = 'python-second', 1.0


def library(name: str, filename: str, dependencies: tuple[str, ...] = (), links: str = '') -> CPPLibraryModule:
    return CPPLibraryModule(
        name, FolderPath(str(ROOT / 'cpp' / name)),
        CPPBuildConfig(f'mkdir -p "$CPP_BUILD_DIR/release" && cc -shared -fPIC library.c -Wl,-soname,{filename} {links} -o "$CPP_BUILD_DIR/release/{filename}"'),
        dependencies=dependencies, outputs=ModuleOutputs(headers=("api.h",)) if name == "base" else ModuleOutputs(),
    )


def get_modules() -> list[Module]:
    # Deliberately declare consumers first; the graph must reorder them.
    return [
        CPPRunnableModule('program', [], Processes.NATIVE, FolderPath(str(ROOT / 'cpp/program')),
            CPPBuildConfig('mkdir -p "$CPP_BUILD_DIR/release" && cc main.c -lchain -o "$CPP_BUILD_DIR/release/main"'),
            'main', dependencies=('chain',), outputs=ModuleOutputs(resources=('assets/*.txt',)), launch=LaunchSettings(accepts_blitz_flags=False)),
        library('chain', 'libchain.so', ('base',), '-lbase'),
        library('base', 'libbase.so'),
        PythonModule('python-one', [], Processes.FIRST, FolderPath(str(ROOT / 'python/python-one')),
            dependencies=('common_one',), entrypoint=PythonEntrypoint(file='main.py'),
            outputs=ModuleOutputs(resources=('assets/*.txt',)), launch=LaunchSettings(accepts_blitz_flags=False)),
        PythonModule('python-two', [], Processes.SECOND, FolderPath(str(ROOT / 'python/python-two')),
            dependencies=('common_two',), entrypoint=PythonEntrypoint(file='other.py'), launch=LaunchSettings(accepts_blitz_flags=False)),
        library('common_one', 'libcommon.so'),
        library('common_two', 'libcommon.so'),
    ]


def pi_name_to_process_types(names: list[str]) -> dict[str, list[Processes]]:
    return {name: [Processes.NATIVE, Processes.FIRST, Processes.SECOND] for name in names}
