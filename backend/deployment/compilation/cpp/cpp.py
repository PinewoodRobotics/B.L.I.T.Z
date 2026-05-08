if __name__ == "__main__" and __package__ is None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import os

from backend.deployment.compilation.util.cpp_build import (
    CPPBuildConfig,
    CPPBuildOptions,
)
from backend.deployment.compilation.util.commands import run_command
from backend.deployment.compilation.util.parsing import parse_output_flags
from backend.deployment.compilation.util.systems import (
    Architecture,
    LinuxDistro,
    PythonVersion,
    SystemId,
)
from backend.deployment.network_api.utils import FilePath, FolderPath


class CPlusPlus:
    _built_modules: dict[str, FolderPath] = {}

    @classmethod
    def compile(
        cls,
        module_name: str,
        system_id: SystemId,
        build_config: CPPBuildConfig,
        local_project_path: FolderPath,
    ) -> FolderPath:
        """
        Compile a C++ module for a given system ID.

        Args:
            module_name: The name of the module to compile.
            system_id: The system ID to compile for.
            build_config: The commands and dependencies needed to build the module.
            local_project_path: The project path, relative to the repository root.

        Returns:
            The path to the compiled module artifacts.
        """

        build_key = f"{system_id.to_build_key()}-{module_name}-{local_project_path}"
        built_path = cls._built_modules.get(build_key)
        if built_path is not None:
            return built_path

        release_path = cls.generic_compile(
            module_name,
            system_id,
            build_config,
            local_project_path,
        )
        cls._built_modules[build_key] = release_path

        return release_path

    @classmethod
    def generic_compile(
        cls,
        module_name: str,
        system_id: SystemId,
        build_config: CPPBuildConfig,
        local_project_path: FolderPath,
    ) -> FolderPath:
        current_file_path = FolderPath(os.path.dirname(os.path.abspath(__file__)))
        dockerfile_path = FilePath(
            os.path.join(
                current_file_path,
                "Dockerfile",
            )
        )
        compile_bash_path = FilePath(os.path.join(current_file_path, "compile.bash"))
        os.chmod(compile_bash_path, 0o755)

        root_path = FolderPath(os.getcwd())
        compile_bash_mount_path = os.path.relpath(compile_bash_path, root_path)

        image_name = f"cpp-{system_id.to_build_key()}-{module_name}"
        docker_build_cmd = [
            "docker",
            "build",
            "--progress=plain",
            "--platform",
            system_id.docker_image,
            "--build-arg",
            f"MODULE_NAME={module_name}",
            "--build-arg",
            f"LINUX_DISTRO={system_id.linux_distro.value}",
            "--build-arg",
            f"CPPLIBRARIES={build_config.libs}",
            "--build-arg",
            f"EXTRA_DOCKER_COMMANDS={build_config.extra_docker_commands}",
            "-f",
            dockerfile_path,
            "-t",
            image_name,
            ".",
        ]

        _ = run_command(
            docker_build_cmd,
            f"Prepare C++ build environment for {module_name}",
        )

        docker_run_cmd = [
            "docker",
            "run",
            "--platform",
            system_id.docker_image,
            "-v",
            f"{root_path}/:/work",
            "--rm",
            "-e",
            f"MODULE_NAME={module_name}",
            "-e",
            f"PROJECT_PATH={local_project_path}",
            "-e",
            f"LINUX_DISTRO={system_id.linux_distro.remove_nonchars()}",
            "-e",
            f"BUILD_CMD={build_config.build_cmd}",
            image_name,
            f"/work/{compile_bash_mount_path}",
        ]

        result_stdout = run_command(
            docker_run_cmd,
            f"Compile C++ module {module_name}",
        )

        flags = parse_output_flags(
            result_stdout,
            ["LINUX_DISTRO", "C_LIB_VERSION", "RESULT_PATH"],
        )

        return FolderPath(flags["RESULT_PATH"])


if __name__ == "__main__":
    release_path = CPlusPlus.compile(
        "test",
        SystemId(
            c_lib_version="2.0.0",
            linux_distro=LinuxDistro.UBUNTU_22,
            architecture=Architecture.AARCH64,
            python_version=PythonVersion(major=3, minor=12),
        ),
        CPPBuildConfig.with_cmake(
            clean_build_dir=False,
            cmake_args=[],
            compiler_args=[CPPBuildOptions.NONE],
            libs=[],
            extra_docker_commands=[],
        ),
        FolderPath("backend/cpp/test"),
    )

    print(release_path)
