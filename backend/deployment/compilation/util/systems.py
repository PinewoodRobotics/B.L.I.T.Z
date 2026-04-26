from dataclasses import dataclass
from enum import Enum
import re


@dataclass
class PythonVersion:
    major: int
    minor: int

    def __str__(self) -> str:
        return f"python{self.major}-{self.minor}"


class Architecture(Enum):
    AMD64 = "amd64"
    ARM64 = "arm64"
    ARM32 = "arm32"
    AARCH64 = "aarch64"

    def to_manylinux_arch_tag(self) -> str:
        match self:
            case Architecture.AMD64:
                return "x86_64"
            case Architecture.ARM64 | Architecture.AARCH64:
                return "aarch64"
            case Architecture.ARM32:
                return "armv7l"
            case _:
                raise ValueError(f"Unsupported architecture: {self}")


class LinuxDistro(Enum):
    UBUNTU = "ubuntu:24.04"
    UBUNTU_22 = "ubuntu:22.04"
    UBUNTU_20 = "ubuntu:20.04"
    JETPACK_L4T_R36_2 = "nvcr.io/nvidia/l4t-cuda:12.2.12-devel"

    DEBIAN_12 = "debian:12"  # Debian 12 Bookworm - GLIBC 2.36
    DEBIAN_11 = "debian:11"  # Debian 11 Bullseye - GLIBC 2.31

    def remove_nonchars(self) -> str:
        return self.value.replace(":", "-").replace(".", "_")


def glibc_to_manylinux_platforms(c_lib_version: str, arch: Architecture) -> list[str]:
    """
    Example:
        c_lib_version="2.39"
        arch=Architecture.AMD64

    Returns:
        manylinux_2_39_x86_64
        manylinux_2_38_x86_64
        ...
        manylinux_2_17_x86_64
        manylinux2014_x86_64
    """
    arch_tag = arch.to_manylinux_arch_tag()

    version = c_lib_version.lower().replace("glibc", "").replace("_", ".").strip(".- ")
    major, minor = map(int, version.split(".")[:2])

    if major != 2:
        raise ValueError(f"Unsupported glibc major version: {major}")

    platforms = [f"manylinux_2_{m}_{arch_tag}" for m in range(minor, 16, -1)]

    platforms.append(f"manylinux2014_{arch_tag}")
    return platforms


@dataclass
class SystemId:
    c_lib_version: str
    linux_distro: LinuxDistro
    architecture: Architecture
    python_version: PythonVersion

    @property
    def docker_image(self) -> str:
        return f"linux/{self.architecture.value}"

    def to_build_key(self) -> str:
        distro = re.sub(r"[^a-zA-Z0-9]+", "-", self.linux_distro.value).strip("-")
        return f"{self.c_lib_version}-{self.architecture.value}-{distro}-{str(self.python_version)}"
