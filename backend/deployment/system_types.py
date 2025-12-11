from dataclasses import dataclass
from enum import Enum
import platform
import subprocess


class SystemType(Enum):
    PI5_BASE_PREBUILT = "pi5-base-prebuilt"
    PI5_BASE = "pi5-base"
    JETPACK_L4T_R36_2 = "jetpack-l4t-r36.2"
    JETPACK_L4T_R35_2 = "jetpack-l4t-r35.2"


class Architecture(Enum):
    AMD64 = "amd64"
    ARM64 = "arm64"
    ARM32 = "arm32"
    AARCH64 = "aarch64"


class LinuxDistro(Enum):
    UBUNTU = "ubuntu:24.04"
    UBUNTU_22 = "ubuntu:22.04"
    UBUNTU_20 = "ubuntu:20.04"
    JETPACK_L4T_R35_2 = "nvcr.io/nvidia/l4t-cuda:11.4.19-devel"
    JETPACK_L4T_R36_2 = "nvcr.io/nvidia/l4t-cuda:12.2.12-devel"

    DEBIAN_12 = "debian:12"  # Debian 12 Bookworm - GLIBC 2.36
    DEBIAN_11 = "debian:11"  # Debian 11 Bullseye - GLIBC 2.31


class DockerPlatformImage(Enum):
    @staticmethod
    def linux_image(platform_type: Architecture) -> tuple[str, Architecture]:
        return ("linux/" + platform_type.value, platform_type)

    LINUX_AMD64 = linux_image(Architecture.AMD64)
    LINUX_ARM64 = linux_image(Architecture.ARM64)
    LINUX_ARM32 = linux_image(Architecture.ARM32)
    LINUX_AARCH64 = linux_image(Architecture.AARCH64)
    JETPACK_L4T_R35_2 = linux_image(Architecture.AARCH64)
    JETPACK_L4T_R36_2 = linux_image(Architecture.AARCH64)


@dataclass
class Platform:
    name: str
    architecture_docker_image: DockerPlatformImage
    linux_distro: LinuxDistro


def get_self_architecture() -> str:
    arch = platform.machine().lower()
    if arch in ("x86_64", "amd64"):
        return "x86_64"
    elif arch in ("aarch64", "arm64"):
        return "aarch64"
    elif arch.startswith("arm"):
        return "arm"
    elif arch in ("i386", "i686", "x86"):
        return "x86"
    return arch


def get_self_ldd_version() -> str:
    # assuming linux machine
    return (
        subprocess.check_output(["ldd", "--version"], text=True)
        .splitlines()[0]
        .split()[-1]
    )
