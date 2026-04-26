from backend.deployment.compilation.util.cpp_build import (
    CPPBuildConfig,
    CPPBuildOptions,
)
from backend.deployment.deployer import BlitzNetworkDeployer
from backend.deployment.misc import output
from backend.deployment.module.supported import SupportedModules
from backend.deployment.processes import WeightedProcess
from backend.deployment.module.base import Module


class ProcessType(WeightedProcess):
    pass


def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return {}


def get_modules() -> list[Module]:
    return [
        SupportedModules.PythonModule(
            name="example",
            module_folder_path="backend/python/example/",
            extra_run_args=[],
            equivalent_run_definition="example",
        ),
        SupportedModules.RustModule(
            name="test",
            runnable_name="test",
            extra_run_args=[],
            equivalent_run_definition="test",
            project_root_folder_path="backend/rust/test",
        ),
        SupportedModules.CPPLibraryModule(
            name="test",
            project_root_folder_path="backend/cpp/test",
            compilation_config=CPPBuildConfig.with_cmake(
                clean_build_dir=False,
                cmake_args=[],
                compiler_args=[CPPBuildOptions.NONE],
                libs=[],
                extra_docker_commands=[],
            ),
        ),
    ]


if __name__ == "__main__":
    output.set_verbosity(False)
    _ = BlitzNetworkDeployer.Options.should_bundle_dependencies(
        True
    ).set_discovery_timeout(2)

    BlitzNetworkDeployer.deploy(
        get_modules(), mapper=pi_name_to_process_types, local_backend_path="backend/"
    )
