import os
import subprocess

from backend.deployment.compilation_util import (
    CPPBuildConfig,
    CPPBuildOptions,
)
from backend.deployment.compilation.util.parsing import parse_output_flags
from backend.deployment.compilation.util.systems import (
    Architecture,
    LinuxDistro,
    SystemId,
)


class CPlusPlus:
    _built_modules: dict[str, str] = {}

    @classmethod
    def compile(
        cls,
        module_name: str,
        system_id: SystemId,
        build_config: CPPBuildConfig,
        local_project_path: str,
    ) -> str:
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
            print("--------------------------------")
            print(f"SKIPPING BUILD: {module_name} already built for {build_key}.")
            print("--------------------------------")
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
        local_project_path: str,
    ) -> str:
        print("--------------------------------")
        print(
            f"USING GENERIC COMPILE FOR {system_id.docker_image} {module_name} {system_id.architecture} {system_id.linux_distro}."
        )
        print("--------------------------------")

        current_file_path = os.path.dirname(os.path.abspath(__file__))
        dockerfile_path = os.path.join(
            current_file_path,
            "Dockerfile",
        )
        compile_bash_path = os.path.join(current_file_path, "compile.bash")
        os.chmod(compile_bash_path, 0o755)

        root_path = os.getcwd()
        compile_bash_mount_path = os.path.relpath(compile_bash_path, root_path)

        image_name = f"cpp-{system_id.to_build_key()}-{module_name}"
        docker_build_cmd = [
            "docker",
            "build",
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

        print("--------------------------------")
        print(f"BUILDING DOCKER IMAGE {image_name}...")
        print("--------------------------------")
        _ = subprocess.run(docker_build_cmd, check=True)

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

        print("--------------------------------")
        print(f"RUNNING DOCKER CONTAINER {image_name}...")
        print("--------------------------------")
        result = subprocess.run(
            docker_run_cmd,
            check=True,
            capture_output=True,
            text=True,
        )

        flags = parse_output_flags(
            result.stdout,
            ["LINUX_DISTRO", "C_LIB_VERSION", "RESULT_PATH"],
        )

        return flags["RESULT_PATH"]


if __name__ == "__main__":
    release_path = CPlusPlus.compile(
        "test",
        SystemId(
            c_lib_version="2.0.0",
            linux_distro=LinuxDistro.UBUNTU_22,
            architecture=Architecture.AARCH64,
        ),
        CPPBuildConfig.with_cmake(
            clean_build_dir=False,
            cmake_args=[],
            compiler_args=[CPPBuildOptions.NONE],
            libs=[],
            extra_docker_commands=[],
        ),
        "backend/cpp/test",
    )

    print(release_path)
