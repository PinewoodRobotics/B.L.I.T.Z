import json
import asyncio
from watchdog.util.logger import info, warning, error, debug
import os
import subprocess

import psutil


from watchdog.process_starter import get_possible_processes, start_process


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

    def append(self, process_type: str):
        if process_type not in self:
            super().append(process_type)
            self.save()

    def remove(self, process_type: str):
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
        loop: asyncio.AbstractEventLoop | None = None,
    ):
        self.processes: dict[
            str,
            subprocess.Popen[str] | None,
        ] = {}
        self.config_path: str = config_path
        self.process_mem: ProcessesMemory = ProcessesMemory.from_file(memory_file)
        self._loop: asyncio.AbstractEventLoop | None = loop

    def set_processes(self, new_processes: list[str]):
        active_processes = self.get_active_processes()
        for process_type in new_processes:
            if process_type not in active_processes:
                self.start_and_monitor_process(process_type)
            else:
                self.stop_process(process_type)

    def start_and_monitor_process(self, process_type: str):
        if process_type in self.get_active_processes():
            info(f"Process {process_type} already running, skipping...")
            return

        self._start_process(process_type)
        self.process_mem.append(process_type)

        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                error(
                    f"No event loop found, skipping process monitoring for {process_type}"
                )
                return

        if self._loop and self._loop.is_running():
            _ = self._loop.call_soon_threadsafe(
                asyncio.create_task, self.monitor_process(process_type)
            )

    def _start_process(self, process_type: str):
        self.processes[process_type] = start_process(process_type, self.config_path)

    def _restore_processes_from_memory(self):
        for process_str in self.process_mem:
            try:
                info(f"Restoring process from memory: {process_str}")
                self.start_and_monitor_process(process_str)
            except (ValueError, KeyError):
                warning(f"Invalid process type in memory: {process_str}")

    def get_active_processes(self):
        return list(self.processes.keys())

    def get_possible_processes(self) -> list[str]:
        return get_possible_processes()

    def ping_processes_and_get_alive(self) -> list[str]:
        alive_processes: list[str] = []
        for process_type, process in self.processes.items():
            if process is None:
                continue

            try:
                _ = process.poll()
                if process.poll() is None:
                    alive_processes.append(process_type)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                debug(f"Process {process_type} already dead or inaccessible")

        return alive_processes

    def stop_process(self, process_type: str):
        self.process_mem.remove(process_type)

        process = self.processes.pop(process_type, None)
        if process is None:
            return

        try:
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)
            for child in children:
                debug(f"Killing child process {child.pid}")
                child.terminate()
            gone, alive = psutil.wait_procs(children, timeout=2)
            for child in alive:
                debug(f"Force killing stubborn child process {child.pid}")
                child.kill()

            process.terminate()
            try:
                process.wait(timeout=2)
            except Exception:
                process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            debug(f"Process {process_type} already dead or inaccessible")

        try:
            process.kill()
        except Exception:
            pass

        info(f"Process {process_type} stopped successfully")

    def abort_all_processes(self):
        info("Start Abort!")
        for process_type in self.processes.keys():
            self.stop_process(process_type)

        info("Aborted Successfully!")

    async def monitor_process(self, process_type: str):
        timer = 0
        while True:
            if process_type not in self.processes.keys():
                timer += 1
                if timer > 10:
                    warning(
                        f"Process {process_type} is not in the processes dictionary, stopping..."
                    )
                    break

                await asyncio.sleep(1)
                continue

            process = self.processes.get(process_type, None)
            timer = 0

            if process is None or process.poll() is not None:
                self.stop_process(process_type)
                self._start_process(process_type)
                if process is not None and process.poll() is not None:
                    warning(f"Process {process_type} is dead, restarting...")
                    error(
                        f"{process.stderr.read() if process.stderr is not None else 'No stderr'}"
                    )

            await asyncio.sleep(1)

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
