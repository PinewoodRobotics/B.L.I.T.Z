from dataclasses import dataclass
from enum import Enum
from collections.abc import Mapping
import re
import json


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

    @classmethod
    def from_machine(cls, machine: str) -> "Architecture":
        normalized = machine.lower().replace("_", "-")
        match normalized:
            case "x86-64":
                return cls.AMD64
            case "aarch64" | "arm64":
                return cls.AARCH64
            case "armv7l" | "armv7" | "armhf":
                return cls.ARM32
            case _:
                try:
                    return cls(normalized)
                except ValueError as error:
                    raise ValueError(f"Unsupported architecture: {machine}") from error

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
    UBUNTU_24 = "ubuntu:24.04"
    UBUNTU_22 = "ubuntu:22.04"
    UBUNTU_20 = "ubuntu:20.04"

    JETPACK_L4T_R36_2 = "nvcr.io/nvidia/l4t-cuda:12.2.12-devel"

    DEBIAN_12 = "debian:12"  # Debian 12 Bookworm - GLIBC 2.36
    DEBIAN_11 = "debian:11"  # Debian 11 Bullseye - GLIBC 2.31

    @classmethod
    def from_os_release(
        cls,
        *,
        os_id: str | None,
        os_id_like: str | None,
        version_id: str | None,
        platform_text: str,
    ) -> "LinuxDistro":
        release_ids = {
            value.lower()
            for value in [os_id, *(os_id_like or "").split()]
            if value
        }

        for distro in cls:
            distro_id, _, distro_version = distro.value.partition(":")
            distro_id = distro_id.rsplit("/", 1)[-1]
            if distro_id in release_ids and version_id == distro_version:
                return distro
            if distro_id in platform_text and distro_version in platform_text:
                return distro

        raise ValueError("Could not infer Linux distro")

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
    capabilities: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if len(dict(self.capabilities)) != len(self.capabilities):
            raise ValueError("Duplicate target capability")
        self.capabilities = tuple(sorted(self.capabilities))

    @classmethod
    def from_plan_system(cls, values: Mapping[str, object]) -> "SystemId":
        return cls(
            capabilities=tuple(sorted(dict(values.get("capabilities", {})).items())),
            c_lib_version=str(values["glibc"]),
            linux_distro=LinuxDistro(str(values["distro"])),
            architecture=Architecture(str(values["architecture"])),
            python_version=PythonVersion(
                major=int(values["python_major"]),
                minor=int(values["python_minor"]),
            ),
        )

    @property
    def docker_image(self) -> str:
        return {
            Architecture.AMD64: "linux/amd64",
            Architecture.ARM64: "linux/arm64",
            Architecture.AARCH64: "linux/arm64",
            Architecture.ARM32: "linux/arm/v7",
        }[self.architecture]

    def to_build_key(self) -> str:
        distro = re.sub(r"[^a-zA-Z0-9]+", "-", self.linux_distro.value).strip("-")
        key = f"{self.c_lib_version}-{self.architecture.value}-{distro}-{str(self.python_version)}"
        if self.capabilities:
            key += "-caps-" + json.dumps(dict(self.capabilities), sort_keys=True, separators=(",", ":")).encode().hex()
        return key

    @classmethod
    def from_build_key(cls, key: str) -> "SystemId":
        """Recover a known target profile from an existing bundle name."""
        key, separator, capabilities_hex = key.partition("-caps-")
        capabilities = tuple(sorted(json.loads(bytes.fromhex(capabilities_hex)).items())) if separator else ()
        match = re.fullmatch(
            r"(?P<glibc>\d+\.\d+)-(?P<arch>amd64|arm64|arm32|aarch64)-"
            r"(?P<distro>.+)-python(?P<major>\d+)-(?P<minor>\d+)",
            key,
        )
        if match is None:
            raise ValueError(f"Invalid system build key: {key}")
        distro = next(
            (
                candidate for candidate in LinuxDistro
                if re.sub(r"[^a-zA-Z0-9]+", "-", candidate.value).strip("-")
                == match.group("distro")
            ),
            None,
        )
        if distro is None:
            raise ValueError(f"Unsupported distro in system build key: {key}")
        return cls(
            capabilities=capabilities,
            c_lib_version=match.group("glibc"),
            linux_distro=distro,
            architecture=Architecture(match.group("arch")),
            python_version=PythonVersion(
                major=int(match.group("major")),
                minor=int(match.group("minor")),
            ),
        )
