"""Build and execute every native artifact from a self-contained sample backend."""

from __future__ import annotations

import os
from pathlib import Path
import platform
import runpy
import shlex
import subprocess
from typing import NamedTuple
from zipfile import ZipFile

import pytest

from backend.deployment.bundler import CodeBundler
from backend.deployment.compilation.system_builder import SystemBuilder
from backend.deployment.compilation.util.systems import Architecture, LinuxDistro, PythonVersion, SystemId
from backend.deployment.network_api.utils import FolderPath
from backend.deployment.compilation.util.cpp_build import CPPBuildConfig
from backend.deployment.module.supported import CPPLibraryModule, PythonModule


SAMPLE_BACKEND = Path(__file__).resolve().parent / "fixtures" / "bundling_backend"


class NativeBundle(NamedTuple):
    root: Path
    key: str
    dependency_image: str
    platform: str
    names: set[str]


@pytest.fixture(scope="module")
def native_bundle(tmp_path_factory: pytest.TempPathFactory) -> NativeBundle:
    test_root = tmp_path_factory.mktemp("native-bundle")
    system_id = SystemId(
        "2.39", LinuxDistro.UBUNTU_24,
        Architecture.from_machine(platform.machine()), PythonVersion(3, 12),
    )
    modules = runpy.run_path(str(SAMPLE_BACKEND / "deploy.py"))["get_modules"]()
    bundler = CodeBundler(
        modules=modules,
        backend_local_path=FolderPath(str(SAMPLE_BACKEND)),
        build_folder_path=FolderPath(str(test_root / "build")),
        output_folder_path=FolderPath(str(test_root / "outputs")),
        system_id=system_id,
    )
    original_directory = Path.cwd()
    try:
        os.chdir(SAMPLE_BACKEND)
        archive = Path(bundler.bundle())
    finally:
        os.chdir(original_directory)
    extracted = test_root / "extracted"
    extracted.mkdir()
    with ZipFile(archive) as bundle:
        names = set(bundle.namelist())
    subprocess.run(["unzip", "-q", str(archive), "-d", str(extracted)], check=True)
    builder = SystemBuilder(system_id, bundler.build_path, bundler.context_path)
    return NativeBundle(extracted, system_id.to_build_key(), builder.dependency_image(), system_id.docker_image, names)


def run_from_bundle(bundle: NativeBundle, command: str) -> str:
    result = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--platform", bundle.platform,
         "--mount", f"type=bind,src={bundle.root},dst=/bundle,readonly",
         bundle.dependency_image, "/bin/bash", "-lc", command],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def test_cpp_library_is_bundled_and_callable(native_bundle: NativeBundle) -> None:
    name = f"{native_bundle.key}/cpp/sample_cpp_library/libsample_cpp_library.so"
    assert name in native_bundle.names
    assert f"{native_bundle.key}/link/cpp/sample_cpp_library/libsample_cpp_library.so" in native_bundle.names
    library = f"/bundle/{name}"
    python = f"import ctypes; print(ctypes.CDLL({library!r}).blitz_cpp_library_value())"
    assert run_from_bundle(native_bundle, f"python3 -c {shlex.quote(python)}") == "42"


def test_cpp_executable_is_bundled_and_runs(native_bundle: NativeBundle) -> None:
    executable = f"{native_bundle.key}/cpp/sample_cpp_executable/sample_cpp_executable"
    library = f"{native_bundle.key}/cpp/sample_cpp_library/libsample_cpp_library.so"
    assert executable in native_bundle.names
    assert run_from_bundle(native_bundle, f"/bundle/{executable} /bundle/{library}") == "43"


def test_rust_library_is_bundled_and_callable(native_bundle: NativeBundle) -> None:
    shared = f"{native_bundle.key}/rust/sample_rust_library/libsample_rust_library.so"
    static = f"{native_bundle.key}/rust/sample_rust_library/libsample_rust_library.a"
    assert shared in native_bundle.names
    assert static in native_bundle.names
    assert f"{native_bundle.key}/link/rust/sample_rust_library/libsample_rust_library.so" in native_bundle.names
    library = f"/bundle/{shared}"
    python = f"import ctypes; print(ctypes.CDLL({library!r}).blitz_rust_library_value())"
    assert run_from_bundle(native_bundle, f"python3 -c {shlex.quote(python)}") == "44"


def test_rust_executable_is_bundled_and_runs(native_bundle: NativeBundle) -> None:
    executable = f"{native_bundle.key}/rust/sample_rust_executable/sample_rust_executable"
    assert executable in native_bundle.names
    assert run_from_bundle(native_bundle, f"/bundle/{executable}") == "45"


def test_orin_python_312_bundle_builds_and_runs_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """JetPack 6's Ubuntu 22.04 needs the installer's managed Python ABI."""
    backend = tmp_path / "backend"
    native = backend / "cpp" / "value"
    process = backend / "python" / "control"
    native.mkdir(parents=True)
    process.mkdir(parents=True)
    (native / "value.cpp").write_text('extern "C" int value() { return 42; }\n')
    (process / "__main__.py").write_text(
        "import ctypes, os, six\n"
        "print(ctypes.CDLL(os.environ['BLITZ_LIB_DIR'] + '/value/libvalue.so').value(), six.__version__)\n"
    )
    (tmp_path / "requirements.txt").write_text("six==1.17.0\n")
    modules = [
        CPPLibraryModule("value", FolderPath(str(native)), CPPBuildConfig(
            'mkdir -p "$CPP_BUILD_DIR/release"; g++ -shared -fPIC value.cpp -o "$CPP_BUILD_DIR/release/libvalue.so"'
        )),
        PythonModule("control", [], None, FolderPath(str(process)), dependencies=("value",)),
    ]
    system = SystemId("2.35", LinuxDistro.UBUNTU_22,
                      Architecture.from_machine(platform.machine()), PythonVersion(3, 12))
    builder = SystemBuilder(system, FolderPath(str(tmp_path / "artifacts")),
                            FolderPath(str(tmp_path / "contexts" / "orin")), FolderPath(str(backend)))
    monkeypatch.chdir(tmp_path)
    builder.prepare(modules, bundle_dependencies=True)
    builder.cache_dependencies()
    builder.build_prepared()
    image = builder.dependency_image()
    # Source-only changes rebuild offline without invalidating cached dependencies.
    (native / "value.cpp").write_text('extern "C" int value() { return 43; }\n')
    builder.prepare(modules, bundle_dependencies=True)
    assert builder.dependency_image() == image
    builder.build_prepared()
    command = (
        "/opt/blitz-python/bin/python3.12 -m venv /tmp/runtime && "
        "/tmp/runtime/bin/pip install --no-index --find-links=/bundle/deps/python six==1.17.0 && "
        "BLITZ_LIB_DIR=/bundle/lib /tmp/runtime/bin/python /bundle/python/control/__main__.py"
    )
    result = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--platform", system.docker_image,
         "--mount", f"type=bind,src={builder.build_path},dst=/bundle,readonly",
         image, "/bin/bash", "-c", command], check=True, capture_output=True, text=True,
    )
    assert result.stdout.strip().endswith("43 1.17.0")
