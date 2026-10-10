"""Self-contained backend used by the Docker artifact tests."""

from pathlib import Path

from backend.deployment.compilation.util.cpp_build import CPPBuildConfig
from backend.deployment.module.supported import SupportedModules
from backend.deployment.network_api.utils import FolderPath


ROOT = Path(__file__).resolve().parent


def get_modules() -> list[SupportedModules._Generic]:
    return [
        SupportedModules.CPPLibraryModule(
            "sample_cpp_library", FolderPath(str(ROOT / "cpp/cpp_library")),
            CPPBuildConfig.with_cmake(),
        ),
        SupportedModules.CPPRunnableModule(
            "sample_cpp_executable", [], None,
            FolderPath(str(ROOT / "cpp/cpp_executable")),
            CPPBuildConfig.with_cmake(), "sample_cpp_executable",
        ),
        SupportedModules.RustLibraryModule(
            "sample_rust_library", FolderPath(str(ROOT / "rust/rust_library")),
        ),
        SupportedModules.RustModule(
            "sample_rust_executable", [], None,
            FolderPath(str(ROOT / "rust/rust_executable")), "sample_rust_executable",
        ),
    ]


def pi_name_to_process_types(_pi_names: list[str]) -> dict:
    return {}
