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
from backend.deployment.compilation_util import (
    CPPBuildConfig,
    CPPBuildOptions,
    CPPLibrary,
)
from backend.deployment.system_types import (
    DockerPlatformImage,
    LinuxDistro,
    Platform,
    SystemType,
)


class CPlusPlus:
    @classmethod
    def compile(
        cls,
        module_name: str,
        system_type: SystemType,
        build_config: CPPBuildConfig,
        local_project_path: str,
    ):
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
                linux_distro=LinuxDistro.JETPACK_L4T_R36_2,
            ),
        }

        if system_type not in platform_configs:
            raise ValueError(f"Unsupported system type: {system_type}")

        platform = platform_configs[system_type]
        cls.generic_compile(
            platform, module_name, system_type, build_config, local_project_path
        )

    @classmethod
    def generic_compile(
        cls,
        platform: Platform,
        module_name: str,
        system_type: SystemType,
        build_config: CPPBuildConfig,
        local_project_path: str,
    ):
        build_distro = platform.linux_distro.value
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dockerfile_path = os.path.join(
            script_dir,
            f"Dockerfile",
        )
        compile_bash_path = os.path.join(script_dir, "compile.bash")
        os.chmod(compile_bash_path, 0o755)
        root_path = os.getcwd()

        image_name = f"cpp-{system_type.value}-{module_name}"
        docker_build_cmd = [
            "docker",
            "build",
            "--progress=plain",
            "--platform",
            platform.architecture_docker_image.value[0],
            "--build-arg",
            f"MODULE_NAME={module_name}",
            "--build-arg",
            f"BUILD_DISTRO={build_distro}",
            "--build-arg",
            f"LINUX_DISTRO={platform.linux_distro.value}",
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
        print(
            f"Running docker build command: {' '.join(str(arg) for arg in docker_build_cmd)}"
        )
        print(f"DEBUG - CPPLIBRARIES value: [{build_config.libs}]")
        print(
            f"DEBUG - EXTRA_DOCKER_COMMANDS value: [{build_config.extra_docker_commands}]"
        )
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
            "-e",
            f"PROJECT_PATH={local_project_path}",
            "-e",
            f"BUILD_CMD={build_config.build_cmd}",
            image_name,
        ]
        _ = subprocess.run(docker_run_cmd, check=True)


if __name__ == "__main__":
    # testing purposes only
    CPlusPlus.compile(
        "cuda_tags",
        SystemType.JETPACK_L4T_R36_2,
        CPPBuildConfig.with_cmake(
            clean_build_dir=False,
            cmake_args=[
                "-DCUDATAGS_BUILD_PYTHON=ON",
            ],
            compiler_args=[CPPBuildOptions.NONE],
            libs=[
                CPPLibrary(name="python3"),
                CPPLibrary(name="python3-dev"),
                CPPLibrary(name="python-is-python3"),
                CPPLibrary(name="python3-numpy"),
                CPPLibrary(name="python3-pip"),
                CPPLibrary(name="python3-distutils"),
                CPPLibrary(name="pybind11-dev"),
                CPPLibrary(name="libopencv-dev"),
                CPPLibrary(name="openjdk-11-jdk"),
                CPPLibrary(name="default-jdk"),
                CPPLibrary(name="cmake"),
                CPPLibrary(name="ninja-build"),
                CPPLibrary(name="pkg-config"),
                CPPLibrary(name="git"),
                CPPLibrary(name="build-essential"),
                CPPLibrary(name="libssl-dev"),
            ],
            extra_docker_commands=[],
        ),
        "cpp/CudaTags",
    )
