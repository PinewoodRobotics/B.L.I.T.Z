import asyncio
import json
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import cast

from pytest import MonkeyPatch

from backend.deployment.module.base import Module as BackendModule
from backend.deployment.module.base import RunnableModule as BackendRunnableModule
from watchdog.constants import BLITZ_PATH, BUNDLE_FOLDER_PATH
from watchdog.monitor import ProcessMonitor, ProcessesMemory
from watchdog.process_starter import OpenedProcess


class FakeProcess:
    def __init__(self, *, alive: bool = True):
        self.alive: bool = alive
        self.stop_calls: int = 0

    def poll(self) -> int | None:
        return None if self.alive else 1

    def is_alive(self) -> bool:
        return self.alive

    def stop(self) -> None:
        self.stop_calls += 1
        self.alive = False


class FakeRunDefinition:
    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        return self.name

    def get_weight(self) -> float:
        return 1.0


class FakeRunnableModule(BackendRunnableModule):
    def get_language_name(self) -> str:
        return "fake"

    def get_run_command(self, bundle_path: str) -> str:
        return f"{bundle_path}/{self.name}"


class FakeNonRunnableModule(BackendModule):
    def get_language_name(self) -> str:
        return "fake"


def make_module(name: str) -> FakeRunnableModule:
    return FakeRunnableModule(
        name=name,
        extra_run_args=[],
        equivalent_run_definition=FakeRunDefinition(name),  # pyright: ignore[reportArgumentType]
    )


class FakeDeploymentModules:
    def __init__(self, starts: dict[str, list[FakeProcess | None]] | None = None):
        self.starts: dict[str, list[FakeProcess | None]] = starts or {}
        self.started: list[tuple[str, str, dict[str, str]]] = []
        self.modules: list[BackendModule] = [
            make_module(process_type) for process_type in self.starts.keys()
        ]

    def start_module(
        self,
        module: BackendRunnableModule,
        bundle_path: str,
        flags: dict[str, str],
    ) -> FakeProcess | None:
        self.started.append((module.name, bundle_path, flags))
        process_type = module.name
        queued_starts = self.starts.setdefault(process_type, [])
        if not queued_starts:
            return None
        return queued_starts.pop(0)

    def get_modules(self) -> list[BackendModule]:
        return self.modules


class FakeLoop:
    def __init__(self):
        self.scheduled_count: int = 0

    def call_soon_threadsafe(
        self,
        _callback: Callable[[Coroutine[object, object, object]], object],
        coroutine: Coroutine[object, object, object],
    ) -> None:
        self.scheduled_count += 1
        coroutine.close()


def write_config(tmp_path: Path) -> str:
    config_file = tmp_path / "config.json"
    _ = config_file.write_text('{"processes": []}')
    return str(config_file)


def read_memory(memory_file: Path) -> list[str]:
    return cast(list[str], json.loads(memory_file.read_text())["processes"])


def as_loop(fake_loop: FakeLoop) -> asyncio.AbstractEventLoop:
    return cast(asyncio.AbstractEventLoop, cast(object, fake_loop))


def as_opened_process(fake_process: FakeProcess) -> OpenedProcess:
    return cast(OpenedProcess, cast(object, fake_process))


def make_monitor(
    tmp_path: Path, deployment_modules: FakeDeploymentModules, monkeypatch: MonkeyPatch
) -> tuple[ProcessMonitor, FakeLoop]:
    monkeypatch.setattr("watchdog.monitor.get_modules", deployment_modules.get_modules)
    monkeypatch.setattr(
        OpenedProcess, "start_module", staticmethod(deployment_modules.start_module)
    )
    fake_loop = FakeLoop()
    process_monitor = ProcessMonitor(
        str(tmp_path / "memory.json"),
        write_config(tmp_path),
        as_loop(fake_loop),
    )
    return process_monitor, fake_loop


def test_processes_memory_creates_empty_file(tmp_path: Path):
    memory_file = tmp_path / "memory.json"

    memory = ProcessesMemory.from_file(str(memory_file))

    assert memory == []
    assert read_memory(memory_file) == []


def test_processes_memory_persists_unique_appends_and_removes(tmp_path: Path):
    memory_file = tmp_path / "memory.json"
    memory = ProcessesMemory.from_file(str(memory_file))

    memory.append("camera")
    memory.append("camera")
    memory.append("localization")
    memory.remove("camera")

    assert memory == ["localization"]
    assert read_memory(memory_file) == ["localization"]


def test_processes_memory_replace_persists_unique_requested_order(tmp_path: Path):
    memory_file = tmp_path / "memory.json"
    memory = ProcessesMemory.from_file(str(memory_file))
    memory.append("stale")

    memory.replace(["camera", "camera", "localization"])

    assert memory == ["camera", "localization"]
    assert read_memory(memory_file) == ["camera", "localization"]


def test_start_and_monitor_process_tracks_process_and_schedules_monitor(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    process = FakeProcess()
    deployment_modules = FakeDeploymentModules({"camera": [process]})
    process_monitor, fake_loop = make_monitor(tmp_path, deployment_modules, monkeypatch)

    process_monitor.start_and_monitor_process("camera")

    assert process_monitor.processes == {"camera": as_opened_process(process)}
    assert process_monitor.process_mem == ["camera"]
    assert read_memory(tmp_path / "memory.json") == ["camera"]
    assert deployment_modules.started[0][1] == BUNDLE_FOLDER_PATH
    assert fake_loop.scheduled_count == 1


def test_watchdog_runtime_bundle_path_matches_installed_backend_path():
    assert BUNDLE_FOLDER_PATH == str(Path(BLITZ_PATH) / "backend")


def test_start_and_monitor_process_ignores_missing_config(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    fake_loop = FakeLoop()
    process_monitor = ProcessMonitor(
        str(tmp_path / "memory.json"),
        str(tmp_path / "missing-config.json"),
        as_loop(fake_loop),
    )
    deployment_modules = FakeDeploymentModules({"camera": [FakeProcess()]})
    monkeypatch.setattr("watchdog.monitor.get_modules", deployment_modules.get_modules)
    monkeypatch.setattr(
        OpenedProcess, "start_module", staticmethod(deployment_modules.start_module)
    )

    process_monitor.start_and_monitor_process("camera")

    assert process_monitor.processes == {}
    assert process_monitor.process_mem == []
    assert deployment_modules.started == []


def test_start_and_monitor_process_does_not_restart_active_process(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    original_process = FakeProcess()
    deployment_modules = FakeDeploymentModules({"camera": [FakeProcess()]})
    process_monitor, _fake_loop = make_monitor(
        tmp_path, deployment_modules, monkeypatch
    )
    process_monitor.processes["camera"] = as_opened_process(original_process)

    process_monitor.start_and_monitor_process("camera")

    assert process_monitor.processes["camera"] is original_process
    assert deployment_modules.started == []


def test_set_processes_starts_missing_and_stops_removed(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    removed_process = FakeProcess()
    added_process = FakeProcess()
    process_monitor, _fake_loop = make_monitor(
        tmp_path, FakeDeploymentModules({"new": [added_process]}), monkeypatch
    )
    process_monitor.processes["old"] = as_opened_process(removed_process)
    process_monitor.process_mem.append("old")

    process_monitor.set_processes(["new"])

    assert removed_process.stop_calls == 1
    assert process_monitor.processes == {"new": as_opened_process(added_process)}
    assert process_monitor.process_mem == ["new"]
    assert read_memory(tmp_path / "memory.json") == ["new"]


def test_set_processes_clears_stale_remembered_processes_that_are_not_active(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    memory_file = tmp_path / "memory.json"
    _ = memory_file.write_text('{"processes": ["test"]}')
    process_monitor, _fake_loop = make_monitor(
        tmp_path, FakeDeploymentModules(), monkeypatch
    )
    process_monitor.process_mem = ProcessesMemory.from_file(str(memory_file))

    process_monitor.set_processes([])

    assert process_monitor.processes == {}
    assert process_monitor.process_mem == []
    assert read_memory(memory_file) == []


def test_stop_process_clears_stale_remembered_process_even_when_not_active(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    process_monitor, _fake_loop = make_monitor(
        tmp_path, FakeDeploymentModules(), monkeypatch
    )
    process_monitor.process_mem.append("test")

    process_monitor.stop_process("test")

    assert process_monitor.processes == {}
    assert process_monitor.process_mem == []
    assert read_memory(tmp_path / "memory.json") == []


def test_ping_processes_and_get_alive_filters_dead_processes(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    process_monitor, _fake_loop = make_monitor(
        tmp_path, FakeDeploymentModules(), monkeypatch
    )
    process_monitor.processes["alive"] = as_opened_process(FakeProcess(alive=True))
    process_monitor.processes["dead"] = as_opened_process(FakeProcess(alive=False))

    assert process_monitor.ping_processes_and_get_alive() == ["alive"]


def test_abort_all_processes_stops_everything_and_clears_memory(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    first_process = FakeProcess()
    second_process = FakeProcess()
    process_monitor, _fake_loop = make_monitor(
        tmp_path, FakeDeploymentModules(), monkeypatch
    )
    process_monitor.processes["first"] = as_opened_process(first_process)
    process_monitor.processes["second"] = as_opened_process(second_process)
    process_monitor.process_mem.append("first")
    process_monitor.process_mem.append("second")

    process_monitor.abort_all_processes()

    assert first_process.stop_calls == 1
    assert second_process.stop_calls == 1
    assert process_monitor.processes == {}
    assert process_monitor.process_mem == []
    assert read_memory(tmp_path / "memory.json") == []


def test_reboot_processes_restarts_remembered_processes(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    old_process = FakeProcess()
    new_process = FakeProcess()
    process_monitor, _fake_loop = make_monitor(
        tmp_path, FakeDeploymentModules({"camera": [new_process]}), monkeypatch
    )
    process_monitor.processes["camera"] = as_opened_process(old_process)
    process_monitor.process_mem.append("camera")

    process_monitor.reboot_processes()

    assert old_process.stop_calls == 1
    assert process_monitor.processes == {"camera": as_opened_process(new_process)}
    assert process_monitor.process_mem == ["camera"]
    assert read_memory(tmp_path / "memory.json") == ["camera"]


def test_get_possible_processes_delegates_to_deployment_modules(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    deployment_modules = FakeDeploymentModules()
    deployment_modules.modules = [
        make_module("camera"),
        FakeNonRunnableModule(name="generated"),
        make_module("localization"),
    ]
    process_monitor, _fake_loop = make_monitor(
        tmp_path, deployment_modules, monkeypatch
    )

    assert process_monitor.get_possible_processes() == ["camera", "localization"]


def test_restore_processes_from_memory_starts_saved_processes(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    camera_process = FakeProcess()
    memory_file = tmp_path / "memory.json"
    _ = memory_file.write_text('{"processes": ["camera"]}')
    deployment_modules = FakeDeploymentModules({"camera": [camera_process]})
    monkeypatch.setattr("watchdog.monitor.get_modules", deployment_modules.get_modules)
    monkeypatch.setattr(
        OpenedProcess, "start_module", staticmethod(deployment_modules.start_module)
    )
    fake_loop = FakeLoop()
    process_monitor = ProcessMonitor(
        str(memory_file),
        write_config(tmp_path),
        as_loop(fake_loop),
    )

    process_monitor._restore_processes_from_memory()  # pyright: ignore[reportPrivateUsage]

    assert process_monitor.processes == {"camera": as_opened_process(camera_process)}
    assert process_monitor.process_mem == ["camera"]


def test_monitor_process_retries_failed_restart_without_forgetting_process(
    tmp_path: Path, monkeypatch: MonkeyPatch
):
    class StopMonitor(Exception):
        pass

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls > 2:
            raise StopMonitor

    old_process = FakeProcess(alive=False)
    replacement_process = FakeProcess(alive=True)
    process_monitor, _fake_loop = make_monitor(
        tmp_path,
        FakeDeploymentModules({"camera": [None, replacement_process]}),
        monkeypatch,
    )
    process_monitor.processes["camera"] = as_opened_process(old_process)
    process_monitor.process_mem.append("camera")
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    try:
        asyncio.run(process_monitor.monitor_process("camera"))
    except StopMonitor:
        pass

    assert old_process.stop_calls == 2
    assert process_monitor.processes["camera"] is replacement_process
    assert process_monitor.process_mem == ["camera"]
    assert read_memory(tmp_path / "memory.json") == ["camera"]
