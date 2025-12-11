from dataclasses import dataclass
from enum import Enum


class CPPBuildOptions(Enum):
    INSTALL = "install"
    NONE = ""


@dataclass
class CPPLibrary:
    name: str
    install_command: str = "apt-get install -y"


def libs_to_string(libs: list[CPPLibrary]) -> str:
    commands = []
    for lib in libs:
        commands.append(f"{lib.install_command} {lib.name}")
    return " && ".join(commands)


class CPPBuildConfig:
    def __init__(
        self,
        build_cmd: str,
        libs: list[CPPLibrary] | None = None,
        extra_docker_commands: list[str] | None = None,
    ):
        self.build_cmd: str = build_cmd
        self.libs: str = (
            libs_to_string(libs) if libs else "echo 'No libraries to install'"
        )
        self.extra_docker_commands: str = (
            " && ".join(extra_docker_commands) if extra_docker_commands else ""
        )

    @classmethod
    def with_cmake(
        cls,
        cmake_lists_path: str = ".",
        cmake_args: list[str] | None = None,
        compiler_cmd: str = "make",
        compiler_args: list[str | CPPBuildOptions] | None = None,
        libs: list[CPPLibrary] | None = None,
        extra_docker_commands: list[str] | None = None,
        clean_build_dir: bool = False,
    ):
        if compiler_args is None:
            compiler_args = []
        compiler_args: list[str] = [
            arg.value if isinstance(arg, CPPBuildOptions) else arg
            for arg in compiler_args
        ]
        if cmake_args is None:
            cmake_args = []

        cmake_args_str = " ".join(cmake_args)
        compiler_args_str = " ".join(compiler_args)

        build_cmd = (
            (f"rm -rf build && " if clean_build_dir else "")
            + f"cmake -B build -S {cmake_lists_path} {cmake_args_str} && "
            + f"cd build && {compiler_cmd} {compiler_args_str}"
        )

        return cls(
            build_cmd=build_cmd,
            libs=libs,
            extra_docker_commands=extra_docker_commands,
        )

    @classmethod
    def with_ninja(
        cls,
        cmake_lists_path: str = "../",
        cmake_args: list[str] | None = None,
        ninja_cmd: str = "ninja",
        ninja_args: list[str | CPPBuildOptions] | None = None,
        libs: list[CPPLibrary] | None = None,
        extra_docker_commands: list[str] | None = None,
        clean_build_dir: bool = False,
    ):
        return cls.with_cmake(
            cmake_lists_path=cmake_lists_path,
            compiler_cmd=ninja_cmd,
            compiler_args=ninja_args,
            cmake_args=cmake_args,
            libs=libs,
            extra_docker_commands=extra_docker_commands,
            clean_build_dir=clean_build_dir,
        )
