"""Conservative local probes for the officially supported target capabilities.

The system catalog owns refresh/caching. This module performs one collection:
one cheap device scan, then only the expensive families with relevant evidence.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys

from backend.deployment.compilation.util.capabilities import (
    Capability,
    CapabilityDetectorFamily,
    LINUX_CAPABILITY_FAMILIES,
    PRESENCE_VALUE,
    normalize_capabilities,
)
from backend.deployment.compilation.util.systems import LinuxDistro


PROBE_TIMEOUT_SECONDS = 3
DEVICE_DIRECTORY = Path("/dev")
_INTERFACE_PATTERNS: Mapping[Capability, re.Pattern[str]] = {
    Capability.V4L2: re.compile(r"video\d+"),
    Capability.I2C: re.compile(r"i2c-\d+"),
    Capability.SPI: re.compile(r"spidev\d+\.\d+"),
    Capability.GPIO: re.compile(r"gpiochip\d+"),
}

# Isolate driver initialization in a bounded process. cuInit + a positive device
# count prevents an installed toolkit or stub libcuda from advertising a GPU.
_CUDA_DRIVER_PROBE = """
import ctypes
driver = ctypes.CDLL('libcuda.so.1')
count = ctypes.c_int()
version = ctypes.c_int()
if driver.cuInit(0) != 0:
    raise SystemExit(1)
if driver.cuDeviceGetCount(ctypes.byref(count)) != 0 or count.value < 1:
    raise SystemExit(1)
if driver.cuDriverGetVersion(ctypes.byref(version)) != 0 or version.value < 1000:
    raise SystemExit(1)
print(f'{version.value // 1000}.{(version.value % 1000) // 10}')
"""


def _accessible_device_names() -> frozenset[str]:
    """Only actual character devices available to this watchdog count."""
    names: set[str] = set()
    try:
        for device in DEVICE_DIRECTORY.iterdir():
            try:
                if stat.S_ISCHR(device.stat().st_mode) and os.access(device, os.R_OK | os.W_OK):
                    names.add(device.name)
            except OSError:
                continue
    except OSError:
        pass
    return frozenset(names)


def _collect_linux_device_interfaces(device_names: frozenset[str]) -> dict[str, str]:
    return {
        capability.value: PRESENCE_VALUE
        for capability, pattern in _INTERFACE_PATTERNS.items()
        if any(pattern.fullmatch(name) for name in device_names)
    }


def _run_nvidia_probe(command: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command, capture_output=True, text=True,
            timeout=PROBE_TIMEOUT_SECONDS, check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _collect_nvidia(device_names: frozenset[str]) -> dict[str, str]:
    """Prefer one SMI query; retry through the driver API if CUDA is unreported."""
    capabilities: dict[str, str] = {}
    if shutil.which("nvidia-smi") is not None:
        result = _run_nvidia_probe(["nvidia-smi"])
        if result is not None and result.returncode == 0 and "No devices were found" not in result.stdout:
            for capability, pattern in (
                (Capability.NVIDIA_DRIVER, r"Driver Version:\s*(\d+(?:\.\d+)*)"),
                (Capability.CUDA, r"CUDA Version:\s*(\d+(?:\.\d+)*)"),
            ):
                match = re.search(pattern, result.stdout)
                if match:
                    capabilities[capability.value] = match.group(1)
    if Capability.CUDA.value not in capabilities:
        result = _run_nvidia_probe([sys.executable, "-c", _CUDA_DRIVER_PROBE])
        if result is not None and result.returncode == 0:
            version = result.stdout.strip()
            if re.fullmatch(r"\d+\.\d+", version):
                capabilities[Capability.CUDA.value] = version
    return capabilities


_DETECTORS: Mapping[CapabilityDetectorFamily, Callable[[frozenset[str]], dict[str, str]]] = {
    CapabilityDetectorFamily.NVIDIA: _collect_nvidia,
    CapabilityDetectorFamily.LINUX_DEVICE_INTERFACES: _collect_linux_device_interfaces,
}


def _candidate_families(os_release: Mapping[str, str]) -> tuple[CapabilityDetectorFamily, ...]:
    try:
        distro = LinuxDistro.from_os_release(
            os_id=os_release.get("ID"), os_id_like=os_release.get("ID_LIKE"),
            version_id=os_release.get("VERSION_ID"), platform_text="",
        )
    except ValueError:
        # Other Linux releases can still report standard local interfaces.
        return LINUX_CAPABILITY_FAMILIES
    return distro.capability_detector_families


def _read_os_release() -> dict[str, str]:
    try:
        return platform.freedesktop_os_release()
    except OSError:
        return {}


def collect_capabilities(
    os_release: Mapping[str, str] | None = None,
    machine_architecture: str | None = None,
) -> dict[str, str]:
    """Report verified capabilities; missing tools/permissions yield absence.

    NVIDIA collection requires accessible device evidence and a successful driver
    probe. Device-interface capabilities promise exposed interfaces only. In Docker,
    only devices passed through and accessible inside the container are advertised.
    """
    release = _read_os_release() if os_release is None else os_release
    if not release and platform.system() != "Linux":
        return {}
    architecture = (machine_architecture or platform.machine()).lower()
    device_names = _accessible_device_names()
    has_nvidia_device = any(
        re.fullmatch(r"nvidia\d+|nvhost-gpu", name) for name in device_names
    )
    capabilities: dict[str, str] = {}
    for family in _candidate_families(release):
        if family is CapabilityDetectorFamily.NVIDIA:
            if (
                architecture not in {"x86_64", "amd64", "aarch64", "arm64", "armv7l", "armhf"}
                or not has_nvidia_device
            ):
                continue
        capabilities.update(_DETECTORS[family](device_names))
    return normalize_capabilities(capabilities)
