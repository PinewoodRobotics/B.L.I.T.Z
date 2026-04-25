import json
import asyncio
import pathlib
from watchdog.process_starter import OpenedProcess, RunnableModules
from watchdog.util.logger import info, warning
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
        self.runnable_modules: RunnableModules = RunnableModules()

    def set_processes(self, new_processes: list[str]):
        current_active = set(self.get_active_processes())
        new_set = set(new_processes)

        to_stop = current_active - new_set
        to_start = new_set - current_active

        for process_type in to_stop:
            self.stop_process(process_type)

        for process_type in to_start:
            self.start_and_monitor_process(process_type)

    def start_and_monitor_process(self, process_type: str):
        if not self.is_config_exists:
            warning(f"Config not set! Cannot start process {process_type}.")
            return

        if process_type in self.get_active_processes():
            info(f"Process {process_type} already running, skipping...")
            return

        process = self.runnable_modules.start_process(process_type, self.config_path)
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
        return self.runnable_modules.get_possible_processes()

    def ping_processes_and_get_alive(self) -> list[str]:
        return [
            process_type
            for process_type in self.processes.keys()
            if self.processes[process_type].is_alive()
        ]

    def stop_process(self, process_type: str):
        self.process_mem.remove(process_type)
        self.processes.pop(process_type).stop()

    def abort_all_processes(self):
        info("Start Abort!")
        for process_type in list(self.processes.keys()):
            self.stop_process(process_type)

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

            if process is None or process.poll() is not None:
                if process is not None:
                    process.stop()
                process = self.runnable_modules.start_process(
                    process_type, self.config_path
                )
                if process is None:
                    warning(f"Failed to restart process {process_type}, retrying...")
                    continue
                self.processes[process_type] = process
                self.process_mem.append(process_type)

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
