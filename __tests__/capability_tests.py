from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from backend.deployment.compilation.util.capabilities import (
    CAPABILITY_DEFINITIONS, Capability, normalize_capabilities,
)
from backend.deployment.compilation.util.systems import Architecture, LinuxDistro, PythonVersion, SystemId
from backend.deployment.module.contracts import CapabilityRequirement, TargetRequirements
from watchdog.util import capabilities as probes


def profile(capabilities: tuple[tuple[str, str], ...] = ()) -> SystemId:
    return SystemId("2.39", LinuxDistro.UBUNTU_24, Architecture.AMD64, PythonVersion(3, 12), capabilities)


def test_registry_is_complete_and_requirement_enum_keeps_wire_names() -> None:
    assert set(CAPABILITY_DEFINITIONS) == set(Capability)
    requirement = CapabilityRequirement(Capability.CUDA, "12.2")
    assert asdict(requirement) == {"name": "cuda", "minimum_version": "12.2"}
    assert json.loads(json.dumps(asdict(requirement))) == asdict(requirement)
    assert TargetRequirements(capabilities=(requirement,)).incompatibilities(profile((("cuda", "12.3"),))) == []


@pytest.mark.parametrize("name", ["camera", "not_a_real_capability", "CUDA", 5])
def test_unknown_requirements_and_catalog_names_are_rejected(name: str) -> None:
    with pytest.raises(ValueError, match="Unsupported capability"):
        CapabilityRequirement(name)
    with pytest.raises(ValueError, match="Unsupported capability"):
        normalize_capabilities({name: "1"})


@pytest.mark.parametrize("values", [
    {"cuda": "unknown"}, {"cuda": 12.2}, {"gpio": "1"},
    [("cuda", "12.2"), ("cuda", "12.3")], "cuda", None,
])
def test_invalid_profiles_cannot_enter_build_cache(values: object) -> None:
    with pytest.raises(ValueError):
        normalize_capabilities(values)
    with pytest.raises(ValueError):
        SystemId.from_plan_system({"glibc": "2.39", "distro": "ubuntu:24.04", "architecture": "amd64", "python_major": 3, "python_minor": 12, "capabilities": values})


def test_presence_capabilities_do_not_invent_version_semantics() -> None:
    requirement = CapabilityRequirement(Capability.I2C)
    assert TargetRequirements(capabilities=(requirement,)).incompatibilities(profile((("i2c", "present"),))) == []
    with pytest.raises(ValueError, match="presence semantics"):
        CapabilityRequirement(Capability.I2C, "1")
    with pytest.raises(ValueError, match="Invalid capability version"):
        CapabilityRequirement(Capability.CUDA, "")


def test_existing_cuda_cache_keys_are_preserved_and_round_trip() -> None:
    target = profile((("cuda", "12.2"),))
    expected = "2.39-amd64-ubuntu-24-04-python3-12-caps-" + b'{"cuda":"12.2"}'.hex()
    assert target.to_build_key() == expected
    assert SystemId.from_build_key(expected) == target
    multiple = profile((("i2c", "present"), ("cuda", "12.2")))
    assert SystemId.from_build_key(multiple.to_build_key()) == multiple
    invalid = expected.partition("-caps-")[0] + "-caps-" + b'{"unknown":"1"}'.hex()
    with pytest.raises(ValueError, match="Unsupported capability"):
        SystemId.from_build_key(invalid)


def test_linux_interfaces_require_accessible_character_devices(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ["video0", "i2c-1", "spidev0.0", "gpiochip0"]:
        (tmp_path / name).symlink_to("/dev/null")
    (tmp_path / "video1").write_text("an ordinary file is not a video device")
    (tmp_path / "video-invalid").symlink_to("/dev/null")
    monkeypatch.setattr(probes, "DEVICE_DIRECTORY", tmp_path)
    monkeypatch.setattr(probes.subprocess, "run", lambda *a, **k: pytest.fail("No NVIDIA hardware; expensive probe must be skipped"))
    release = {"ID": "ubuntu", "VERSION_ID": "24.04"}
    assert probes.collect_capabilities(release, "aarch64") == {"gpio": "present", "i2c": "present", "spi": "present", "v4l2": "present"}
    monkeypatch.setattr(probes.os, "access", lambda *a: False)
    assert probes.collect_capabilities(release, "aarch64") == {}


def test_installed_nvidia_tool_or_distro_never_proves_hardware(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probes, "_accessible_device_names", lambda: frozenset())
    monkeypatch.setattr(probes.shutil, "which", lambda _: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(probes.subprocess, "run", lambda *a, **k: pytest.fail("Tool installation is not GPU evidence"))
    assert probes.collect_capabilities({"ID": "ubuntu", "VERSION_ID": "22.04"}, "aarch64") == {}


def nvidia_device(monkeypatch: pytest.MonkeyPatch, tool: bool = True) -> None:
    monkeypatch.setattr(probes, "_accessible_device_names", lambda: frozenset({"nvidia0"}))
    monkeypatch.setattr(probes.shutil, "which", lambda _: "/usr/bin/nvidia-smi" if tool else None)


def test_nvidia_family_collects_two_capabilities_with_one_bounded_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    nvidia_device(monkeypatch)
    calls = []
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "Driver Version: 550.54.15    CUDA Version: 12.4")
    monkeypatch.setattr(probes.subprocess, "run", run)
    assert probes.collect_capabilities({"ID": "debian", "VERSION_ID": "12"}, "x86_64") == {"cuda": "12.4", "nvidia_driver": "550.54.15"}
    assert len(calls) == 1
    assert calls[0][0] == ["nvidia-smi"]
    assert calls[0][1]["timeout"] == 3


@pytest.mark.parametrize("result", [
    subprocess.CompletedProcess([], 1, "Driver Version: 550.54.15 CUDA Version: 12.4"),
    subprocess.CompletedProcess([], 0, "CUDA Version: N/A"),
    subprocess.CompletedProcess([], 0, "No devices were found CUDA Version: 12.4"),
    FileNotFoundError("nvidia-smi"), subprocess.TimeoutExpired("nvidia-smi", 3),
])
def test_failed_nvidia_probes_never_advertise_cuda(monkeypatch: pytest.MonkeyPatch, result: object) -> None:
    nvidia_device(monkeypatch)
    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess:
        if isinstance(result, Exception):
            raise result
        return result
    monkeypatch.setattr(probes.subprocess, "run", run)
    assert probes.collect_capabilities({"ID": "ubuntu"}, "x86_64") == {}


@pytest.mark.parametrize("smi_result,expected", [
    (subprocess.CompletedProcess([], 1, "Driver Version: 550.54.15 CUDA Version: 12.4"), {"cuda": "10.2"}),
    (subprocess.CompletedProcess([], 0, "CUDA Version: N/A"), {"cuda": "10.2"}),
    (subprocess.CompletedProcess([], 0, "No devices were found"), {"cuda": "10.2"}),
    (subprocess.CompletedProcess([], 0, "Driver Version: 550.54.15 CUDA Version: N/A"), {"cuda": "10.2", "nvidia_driver": "550.54.15"}),
    (FileNotFoundError("nvidia-smi"), {"cuda": "10.2"}),
    (subprocess.TimeoutExpired("nvidia-smi", 3), {"cuda": "10.2"}),
])
def test_driver_api_recovers_cuda_after_failed_or_uninformative_smi(
    monkeypatch: pytest.MonkeyPatch, smi_result: object, expected: dict[str, str],
) -> None:
    nvidia_device(monkeypatch)
    commands = []
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        commands.append(command)
        assert kwargs["timeout"] == 3
        if command == ["nvidia-smi"]:
            if isinstance(smi_result, Exception):
                raise smi_result
            return smi_result
        assert command[1] == "-c"
        return subprocess.CompletedProcess(command, 0, "10.2\n")
    monkeypatch.setattr(probes.subprocess, "run", run)
    assert probes.collect_capabilities({"ID": "ubuntu"}, "aarch64") == expected
    assert len(commands) == 2


def test_failed_driver_api_preserves_a_successful_smi_driver_version(monkeypatch: pytest.MonkeyPatch) -> None:
    nvidia_device(monkeypatch)
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        if command == ["nvidia-smi"]:
            return subprocess.CompletedProcess(command, 0, "Driver Version: 550.54.15 CUDA Version: N/A")
        return subprocess.CompletedProcess(command, 1, "")
    monkeypatch.setattr(probes.subprocess, "run", run)
    assert probes.collect_capabilities({"ID": "ubuntu"}, "aarch64") == {"nvidia_driver": "550.54.15"}


@pytest.mark.parametrize("returncode,output,expected", [
    (0, "10.2\n", {"cuda": "10.2"}), (1, "12.2", {}), (0, "unexpected output", {}),
])
def test_jetson_driver_api_probe_needs_success_and_a_valid_version(monkeypatch: pytest.MonkeyPatch, returncode: int, output: str, expected: dict[str, str]) -> None:
    nvidia_device(monkeypatch, tool=False)
    monkeypatch.setattr(probes, "_accessible_device_names", lambda: frozenset({"nvhost-gpu"}))
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        assert command[1] == "-c"
        assert "cuInit" in command[2] and "cuDeviceGetCount" in command[2]
        assert kwargs["timeout"] == 3
        return subprocess.CompletedProcess(command, returncode, output)
    monkeypatch.setattr(probes.subprocess, "run", run)
    assert probes.collect_capabilities({"ID": "ubuntu", "VERSION_ID": "20.04"}, "aarch64") == expected


@pytest.mark.parametrize("init_error,count_error,count,version_error,version,expected", [
    (0, 0, 1, 0, 10020, "10.2"),
    (1, 0, 1, 0, 10020, None),
    (0, 1, 1, 0, 10020, None),
    (0, 0, 0, 0, 10020, None),
    (0, 0, 1, 1, 10020, None),
    (0, 0, 1, 0, 0, None),
])
def test_driver_api_requires_an_initialized_real_device(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    init_error: int, count_error: int, count: int, version_error: int,
    version: int, expected: str | None,
) -> None:
    def get_count(pointer: SimpleNamespace) -> int:
        pointer.value = count
        return count_error
    def get_version(pointer: SimpleNamespace) -> int:
        pointer.value = version
        return version_error
    driver = SimpleNamespace(
        cuInit=lambda _: init_error,
        cuDeviceGetCount=get_count,
        cuDriverGetVersion=get_version,
    )
    monkeypatch.setitem(sys.modules, "ctypes", SimpleNamespace(
        CDLL=lambda _: driver,
        c_int=lambda: SimpleNamespace(value=0),
        byref=lambda value: value,
    ))
    if expected is None:
        with pytest.raises(SystemExit):
            exec(probes._CUDA_DRIVER_PROBE, {})
        assert capsys.readouterr().out == ""
    else:
        exec(probes._CUDA_DRIVER_PROBE, {})
        assert capsys.readouterr().out.strip() == expected
