"""Typed module build and launch contracts shared by deployment and watchdog."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re

from backend.deployment.compilation.util.systems import Architecture, LinuxDistro, SystemId


def relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or '..' in path.parts:
        raise ValueError(f'Expected a path inside the module: {value!r}')
    return value


@dataclass(frozen=True)
class CapabilityRequirement:
    name: str
    minimum_version: str | None = None

    def __post_init__(self) -> None:
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', self.name):
            raise ValueError(f'Invalid capability name: {self.name}')
        if self.minimum_version and not re.fullmatch(r'\d+(\.\d+)*', self.minimum_version):
            raise ValueError(f'Invalid capability version: {self.minimum_version}')


@dataclass(frozen=True)
class TargetRequirements:
    architectures: tuple[Architecture, ...] = ()
    distros: tuple[LinuxDistro, ...] = ()
    python_versions: tuple[tuple[int, int], ...] = ()
    capabilities: tuple[CapabilityRequirement, ...] = ()

    def incompatibilities(self, system: SystemId) -> list[str]:
        reasons = []
        architecture = system.architecture.to_manylinux_arch_tag()
        if self.architectures and architecture not in {a.to_manylinux_arch_tag() for a in self.architectures}:
            reasons.append(f'architecture {system.architecture.value}')
        if self.distros and system.linux_distro not in self.distros:
            reasons.append(f'distro {system.linux_distro.value}')
        python = (system.python_version.major, system.python_version.minor)
        if self.python_versions and python not in self.python_versions:
            reasons.append(f'Python {python[0]}.{python[1]}')
        available = dict(system.capabilities)
        for requirement in self.capabilities:
            version = available.get(requirement.name)
            if version is None:
                reasons.append(f'missing capability {requirement.name}')
            elif requirement.minimum_version:
                def parts(value: str) -> tuple[int, ...]:
                    if not re.fullmatch(r'\d+(\.\d+)*', value):
                        raise ValueError(f'Invalid capability version: {value}')
                    return tuple(int(part) for part in value.split('.'))
                actual, minimum = parts(version), parts(requirement.minimum_version)
                length = max(len(actual), len(minimum))
                if actual + (0,) * (length - len(actual)) < minimum + (0,) * (length - len(minimum)):
                    reasons.append(f'{requirement.name} {version} < {requirement.minimum_version}')
        return reasons


@dataclass(frozen=True)
class ModuleOutputs:
    """Native outputs are relative to build artifacts; headers/resources to source."""
    executables: tuple[str, ...] = ()
    libraries: tuple[str, ...] = ()
    headers: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for pattern in (*self.executables, *self.libraries, *self.headers, *self.resources):
            relative_path(pattern)


@dataclass(frozen=True)
class PythonEntrypoint:
    file: str | None = '__main__.py'
    package: str | None = None

    def __post_init__(self) -> None:
        if (self.file is None) == (self.package is None):
            raise ValueError('Specify exactly one Python entry file or package')
        if self.file is not None:
            relative_path(self.file)
        if self.package is not None and not re.fullmatch(r'[A-Za-z_]\w*(\.[A-Za-z_]\w*)*', self.package):
            raise ValueError(f'Invalid Python package: {self.package}')


@dataclass(frozen=True)
class LaunchSettings:
    arguments: tuple[str, ...] = ()
    working_directory: str = '.'
    environment: tuple[tuple[str, str], ...] = ()
    accepts_blitz_flags: bool = False  # Runtime metadata is supplied through the environment.

    def __post_init__(self) -> None:
        relative_path(self.working_directory)
