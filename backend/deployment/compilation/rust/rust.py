import os
import subprocess

from backend.deployment.compilation.util.parsing import parse_output_flags
from backend.deployment.compilation.util.systems import (
    Architecture,
    LinuxDistro,
    SystemId,
)


class Rust:
    _built_architectures: set[str] = set()

    @classmethod
    def compile(cls, module_name: str, system_id: SystemId) -> str:
        """
        Compile a Rust module for a given system ID.

        Args:
            module_name: The name of the module to compile.
            system_id: The system ID to compile for.

        Returns:
            The path to the compiled module.
        """

        if system_id.to_build_key() in cls._built_architectures:
            print("--------------------------------")
            print(
                f"SKIPPING BUILD: {module_name} already built for {system_id.to_build_key()}."
            )
            print("--------------------------------")
            return ""

        cls._built_architectures.add(system_id.to_build_key())
        return cls.generic_compile(module_name, system_id)

    @classmethod
    def generic_compile(cls, module_name: str, system_id: SystemId) -> str:
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

        image_name = f"rust-{system_id.to_build_key()}-{module_name}"

        docker_build_cmd = [
            "docker",
            "build",
            "--platform",
            system_id.docker_image,
            "--build-arg",
            f"MODULE_NAME={module_name}",
            "--build-arg",
            f"LINUX_DISTRO={system_id.linux_distro.value}",
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
            f"LINUX_DISTRO={system_id.linux_distro.remove_nonchars()}",
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
    system_id = SystemId(
        c_lib_version="2.0.0",
        linux_distro=LinuxDistro.UBUNTU_22,
        architecture=Architecture.AARCH64,
    )

    release_path = Rust.compile("test", system_id)

    print(release_path)
