from dataclasses import dataclass
from enum import Enum


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

    def remove_nonchars(self) -> str:
        return self.value.replace(":", "-").replace(".", "_")


@dataclass
class SystemId:
    c_lib_version: str
    linux_distro: LinuxDistro
    architecture: Architecture

    @property
    def docker_image(self) -> str:
        return f"linux/{self.architecture.value}"

    def to_build_key(self) -> str:
        return (
            f"{self.c_lib_version}-{self.architecture.value}-{self.linux_distro.value}"
        )
