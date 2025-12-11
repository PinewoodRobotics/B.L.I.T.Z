if __name__ == "__main__":
    import sys
    from pathlib import Path

    # for local testing insert this
    script_dir = Path(__file__).parent
    src_dir = (
        script_dir.parent.parent.parent.parent
    )  # src/backend/compilation/rust -> src/
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

import os
import subprocess

from backend.deployment.system_types import (
    Architecture,
    DockerPlatformImage,
    LinuxDistro,
    Platform,
    SystemType,
)


class Rust:
    _built_architectures: set[tuple[str, Architecture]] = set()

    @classmethod
    def compile(cls, module_name: str, system_type: SystemType):
        platform_configs = {
            SystemType.PI5_BASE_PREBUILT: Platform(
                name="pi5-base",
                architecture_docker_image=DockerPlatformImage.LINUX_AARCH64,
                linux_distro=LinuxDistro.DEBIAN_12,
            ),
            SystemType.PI5_BASE: Platform(
                name="pi5-base",
                architecture_docker_image=DockerPlatformImage.LINUX_AARCH64,
                linux_distro=LinuxDistro.UBUNTU,
            ),
            SystemType.JETPACK_L4T_R36_2: Platform(
                name="jetpack-l4t-r35.2",
                architecture_docker_image=DockerPlatformImage.LINUX_AARCH64,
                linux_distro=LinuxDistro.JETPACK_L4T_R35_2,
            ),
        }

        if system_type not in platform_configs:
            raise ValueError(f"Unsupported system type: {system_type}")

        platform = platform_configs[system_type]
        architecture = platform.architecture_docker_image.value[1]

        build_key = (module_name, architecture)
        if build_key in cls._built_architectures:
            print("--------------------------------")
            print(
                f"SKIPPING BUILD: {module_name} already built for {architecture.value} architecture."
            )
            print("--------------------------------")
            return

        cls._built_architectures.add(build_key)
        cls.generic_compile(platform, module_name, system_type)

    @classmethod
    def generic_compile(
        cls, platform: Platform, module_name: str, system_type: SystemType
    ):
        build_distro = platform.linux_distro.value
        print("--------------------------------")
        print(
            f"USING GENERIC COMPILE FOR {platform.name} {module_name} {system_type.value}."
        )
        print(f"Target distro: {build_distro}")
        print("--------------------------------")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dockerfile_path = os.path.join(
            script_dir,
            f"Dockerfile",
        )
        compile_bash_path = os.path.join(script_dir, "compile.bash")
        os.chmod(compile_bash_path, 0o755)
        root_path = os.getcwd()

        image_name = f"rust-{system_type.value}-{module_name}"

        print(platform.architecture_docker_image.value[0])
        print(platform.architecture_docker_image.value[1])
        print(build_distro)

        docker_build_cmd = [
            "docker",
            "build",
            "--platform",
            platform.architecture_docker_image.value[0],
            "--build-arg",
            f"MODULE_NAME={module_name}",
            "--build-arg",
            f"BUILD_DISTRO={build_distro}",
            "--build-arg",
            f"LINUX_DISTRO={platform.linux_distro.value}",
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
            platform.architecture_docker_image.value[0],
            "-v",
            f"{root_path}/:/work",
            "--rm",
            "-e",
            f"MODULE_NAME={module_name}",
            "-e",
            f"PLATFORM_NAME={platform.architecture_docker_image.value[1].value}",
            image_name,
        ]

        print("--------------------------------")
        print(f"RUNNING DOCKER CONTAINER {image_name}...")
        print("--------------------------------")
        _ = subprocess.run(docker_run_cmd, check=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python rust.py <module_name>")
        sys.exit(1)

    module_name = sys.argv[1]
    Rust.compile(module_name, SystemType.JETPACK_L4T_R35_2)
