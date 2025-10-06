import json
import asyncio
from dataclasses import dataclass
from logging import debug, info, warning
import os
import subprocess

import psutil


from backend.python.common.util.system import ProcessType
from watchdog.process_starter import start_process


class ProcessesMemory(list[str]):
    def __init__(self, processes: list[str], file_path: str):
        super().__init__(processes)
        self.file_path = file_path

    @staticmethod
    def from_file(file_path: str) -> "ProcessesMemory":
        if not os.path.exists(file_path):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                json.dump({"processes": []}, f)

            return ProcessesMemory([], file_path)

        with open(file_path, "r") as f:
            data = json.load(f)
            return ProcessesMemory(data.get("processes", []), file_path)

    def save(self):
        with open(self.file_path, "w") as f:
            json.dump({"processes": self}, f)


class ProcessMonitor:
    def __init__(
        self,
        memory_file: str,
        config_path: str,
    ):
        self.processes: dict[
            str,
            subprocess.Popen[str] | None,
        ] = {}
        self.config_path: str = config_path
        self.process_mem: ProcessesMemory = ProcessesMemory.from_file(memory_file)
        self._loop: asyncio.AbstractEventLoop | None = None

    def start_and_monitor_process(self, process_type: str):
        if process_type not in self.process_mem:
            self.process_mem.append(process_type)
            self.process_mem.save()

        process = start_process(process_type, self.config_path)
        if process is None:
            return

        self.processes[process_type] = process
        loop = self._loop
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
        if loop and loop.is_running():
            loop.call_soon_threadsafe(
                asyncio.create_task, self.monitor_process(process_type)
            )

    def _start_process(self, process_type: str):
        if process_type not in self.process_mem:
            self.process_mem.append(process_type)
            self.process_mem.save()

        process = start_process(process_type, self.config_path)
        assert process is not None
        self.processes[process_type] = process

    def _restore_processes_from_memory(self):
        for process_str in self.process_mem:
            try:
                if process_str not in self.processes:
                    info(f"Restoring process from memory: {process_str}")
                    self.start_and_monitor_process(process_str)
            except (ValueError, KeyError):
                warning(f"Invalid process type in memory: {process_str}")

    def get_active_processes(self):
        return self.processes.keys()

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
        if process_type in self.process_mem:
            self.process_mem.remove(process_type)
            self.process_mem.save()

        process = self.processes.get(process_type)
        if process is None:
            return

        info(f"Stopping process {process_type}")

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

        del self.processes[process_type]
        info(f"Process {process_type} stopped successfully")

    def abort_all_processes(self):
        info("Start Abort!")
        processes_to_abort = list(self.processes.keys())
        for process_type in processes_to_abort:
            self.stop_process(process_type)

        info("Aborted Successfully!")

    async def monitor_process(self, process_type: str):
        timer = 0
        while True:
            if process_type not in self.processes:
                timer += 1
                if timer > 10:
                    warning(
                        f"Process {process_type} is not in the processes dictionary, stopping..."
                    )
                    break

                await asyncio.sleep(1)
                continue

            process = self.processes.get(process_type)
            timer = 0

            if process is None or process.poll() is not None:
                warning(f"Process {process_type} is dead, restarting...")
                self.stop_process(process_type)
                self._start_process(process_type)

            await asyncio.sleep(1)

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
