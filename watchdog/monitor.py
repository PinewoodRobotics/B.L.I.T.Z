import json
import asyncio
import pathlib
from watchdog.constants import (
    BASIC_SYSTEM_CONFIG_PATH,
    BLITZ_PATH,
    BUNDLE_FOLDER_PATH,
    SYSTEM_NAME,
)
from watchdog.ext.expected_deployment_struct import RunnableModule, get_modules
from watchdog.process_starter import OpenedProcess
from watchdog.util.lazy_importer import LazyImportError
from watchdog.util.logger import debug, error, info, warning
import os


class ProcessesMemory(list[str]):
    def __init__(self, processes: list[str], file_path: str):
        super().__init__(processes)
        self.file_path: str = file_path

    @staticmethod
    def from_file(file_path: str) -> "ProcessesMemory":
        ProcessesMemory.__verify_non_empty(file_path)

        f = open(file_path, "r")
        data: list[str] = (
            json.load(f).get("processes", []) or []  # pyright: ignore[reportAny]
        )

        f.close()

        return ProcessesMemory(data, file_path)

    def append(self, process_type: str):  # pyright: ignore[reportImplicitOverride]
        if process_type not in self:
            super().append(process_type)
            self.save()

    def remove(self, process_type: str):  # pyright: ignore[reportImplicitOverride]
        if process_type in self:
            super().remove(process_type)
            self.save()

    def replace(self, processes: list[str]):
        super().clear()
        for process_type in processes:
            if process_type not in self:
                super().append(process_type)
        self.save()

    @staticmethod
    def __verify_non_empty(file_path: str):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            with open(file_path, "w") as f:
                json.dump({"processes": []}, f)

    def save(self):
        ProcessesMemory.__verify_non_empty(self.file_path)
        with open(self.file_path, "w") as f:
            json.dump({"processes": self}, f)


class ProcessMonitor:
    def __init__(
        self,
        memory_file: str,
        config_path: str,
        loop: asyncio.AbstractEventLoop,
    ):
        self.processes: dict[
            str,
            OpenedProcess,
        ] = {}
        self.config_path: str = config_path
        self.process_mem: ProcessesMemory = ProcessesMemory.from_file(memory_file)
        self._loop: asyncio.AbstractEventLoop = loop
        self.is_config_exists: bool = (
            pathlib.Path(config_path).exists()
            and pathlib.Path(config_path).is_file()
            and os.path.getsize(config_path) > 0
        )

    def set_processes(self, new_processes: list[str]):
        current_active = set(self.get_active_processes())
        new_set = set(new_processes)

        to_stop = current_active - new_set
        to_start = new_set - current_active

        for process_type in to_stop:
            self.stop_process(process_type)

        self.process_mem.replace(new_processes)

        for process_type in to_start:
            self.start_and_monitor_process(process_type)

    def start_and_monitor_process(self, process_type: str):
        if not self.is_config_exists:
            warning(f"Config not set! Cannot start process {process_type}.")
            return
        if process_type in self.get_active_processes():
            info(f"Process {process_type} already running, skipping...")
            return

        debug(f"Starting process {process_type}")
        process = self.start_process(process_type)
        if process is None:
            warning(f"Failed to start process {process_type}, skipping...")
            return

        self.processes[process_type] = process
        self.process_mem.append(process_type)

        _ = self._loop.call_soon_threadsafe(
            asyncio.create_task, self.monitor_process(process_type)
        )

    # todo: make it wait a bit and then try again maybe? some other solution?
    def _restore_processes_from_memory(self):
        if not self.is_config_exists:
            warning(f"Config not set! Cannot restore processes from memory.")
            return

        for process_str in self.process_mem:
            try:
                info(f"Restoring process from memory: {process_str}")
                self.start_and_monitor_process(process_str)
            except (ValueError, KeyError):
                warning(f"Invalid process type in memory: {process_str}")

    def get_active_processes(self):
        return list(self.processes.keys())

    def get_possible_processes(self) -> list[str]:
        possible_processes: list[str] = []
        for module in get_modules():
            if isinstance(module, RunnableModule):
                possible_processes.append(module.equivalent_run_definition.get_name())

        return possible_processes

    def ping_processes_and_get_alive(self) -> list[str]:
        return [
            process_type
            for process_type in self.processes.keys()
            if self.processes[process_type].is_alive()
        ]

    def stop_process(self, process_type: str):
        self.process_mem.remove(process_type)
        process = self.processes.pop(process_type, None)
        if process is not None:
            process.stop()

    def abort_all_processes(self):
        info("Start Abort!")
        for process_type in list(self.processes.keys()):
            self.stop_process(process_type)
        self.process_mem.replace([])

        info("Aborted Successfully!")

    def refresh_config(self):
        self.reboot_processes()
        self.is_config_exists = (
            pathlib.Path(self.config_path).exists()
            and pathlib.Path(self.config_path).is_file()
            and os.path.getsize(self.config_path) > 0
        )

    def reboot_processes(self):
        info("Start reboot!")
        process_types_to_restore = list(self.process_mem)
        for process_type in list(self.processes.keys()):
            self.processes.pop(process_type).stop()

        for process_type in process_types_to_restore:
            self.start_and_monitor_process(process_type)

        info("Rebooted Successfully!")

    def start_process(self, process_type: str) -> OpenedProcess | None:
        module = next(
            (module for module in get_modules() if module.name == process_type),
            None,
        )

        if module is None or not isinstance(module, RunnableModule):
            debug(f"Process {process_type} is not a valid RunnableModule, skipping...")
            return None

        try:
            process = OpenedProcess.start_module(
                module,
                BUNDLE_FOLDER_PATH,
                {
                    "config-path": self.config_path,
                    "basic-system-config-path": BASIC_SYSTEM_CONFIG_PATH,
                    "blitz-path": BLITZ_PATH,
                    "bundle-folder-path": BUNDLE_FOLDER_PATH,
                    "system-name": SYSTEM_NAME,
                },
            )
        except LazyImportError as e:
            error(f"Failed to start process {process_type}: {e}")
            return
        except Exception as e:
            error(f"Failed to start process {process_type}: {e}")
            return
        return process

    async def monitor_process(self, process_type: str):
        timer = 0
        while True:
            await asyncio.sleep(1)
            if process_type not in self.processes.keys():
                timer += 1
                if timer > 10:
                    warning(
                        f"Process {process_type} is not in the processes dictionary, stopping..."
                    )
                    break
                continue

            process = self.processes.get(process_type, None)
            timer = 0

            if process is None or not process.is_alive():
                return_code = process.poll() if process is not None else None
                warning(
                    f"Process {process_type} exited with code {return_code}; restarting..."
                )
                if process is not None:
                    process.stop()

                process = self.start_process(process_type)
                if process is None:
                    warning(f"Failed to restart process {process_type}, retrying...")
                    continue

                self.processes[process_type] = process
                self.process_mem.append(process_type)
                info(f"Restarted process {process_type}")

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
