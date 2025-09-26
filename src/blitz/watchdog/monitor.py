import json
import asyncio
from dataclasses import dataclass
from logging import debug, info, warning
import os
import subprocess
from typing import Dict, List, Optional

import psutil


from blitz.common.util.system import ProcessType
from blitz.watchdog.process_starter import start_process


@dataclass
class ProcessesMemory:
    processes: list[str]


class ProcessMonitor:
    def __init__(
        self,
        last_processes_file: str,
        event_loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self.processes: Dict[
            ProcessType,
            subprocess.Popen | None,  # pyright: ignore[reportMissingTypeArgument]
        ] = (  # pyright: ignore[reportMissingTypeArgument]
            {}
        )  # pyright: ignore[reportMissingTypeArgument]
        self.process_args: Dict[ProcessType, List[str]] = {}
        self.config_path: str = ""
        self.event_loop = event_loop

        self.process_mem = ProcessesMemory([])
        self.last_processes_file = last_processes_file

        config_dir = os.path.dirname(last_processes_file)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        if os.path.exists(last_processes_file):
            try:
                with open(last_processes_file, "r") as f:
                    data = json.load(f)
                    self.process_mem = ProcessesMemory(data.get("processes", []))
            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                warning(
                    f"Failed to load processes from {last_processes_file}, starting with empty list"
                )
                self.process_mem = ProcessesMemory([])
        else:
            with open(last_processes_file, "w") as f:
                json.dump({"processes": []}, f)

        self._normalize_process_mem()

        # Defer restoring processes until config path is set

    def start_and_monitor_process(
        self, process_type: ProcessType, override: bool = False
    ):
        if self.config_path == "":
            raise ValueError("Config path not set")

        if process_type.value not in self.process_mem.processes:
            self.process_mem.processes.append(process_type.value)
            self.save_process_mem()

        process = start_process(process_type, self.config_path)
        self.processes[process_type] = process
        if self.event_loop:
            asyncio.run_coroutine_threadsafe(
                self.monitor_process(process_type), self.event_loop
            )
        else:
            asyncio.create_task(self.monitor_process(process_type))

    def set_config_path(self, config_path: str):
        self.config_path = config_path
        self._restore_processes_from_memory()

    def _restore_processes_from_memory(self):
        for process_str in self.process_mem.processes:
            try:
                try:
                    process_type = ProcessType(process_str)
                except ValueError:
                    process_type = ProcessType[process_str]  # type: ignore[index]

                if process_type not in self.processes:
                    info(f"Restoring process from memory: {process_type}")
                    proc = start_process(process_type, self.config_path)
                    self.processes[process_type] = proc
                    if self.event_loop:
                        asyncio.run_coroutine_threadsafe(
                            self.monitor_process(process_type), self.event_loop
                        )
                    else:
                        asyncio.create_task(self.monitor_process(process_type))
            except (ValueError, KeyError):
                warning(f"Invalid process type in memory: {process_str}")

    def _normalize_process_mem(self):
        normalized: list[str] = []
        for entry in self.process_mem.processes:
            try:
                try:
                    p = ProcessType(entry)
                except ValueError:
                    p = ProcessType[entry]  # type: ignore[index]
                val = p.value
                if val not in normalized:
                    normalized.append(val)
            except (ValueError, KeyError):
                warning(f"Skipping invalid process entry in memory: {entry}")
        self.process_mem.processes = normalized
        self.save_process_mem()

    def get_active_processes(self):
        return self.processes.keys()

    def ping_processes_and_get_alive(self):
        alive_processes = []
        for process_type, process in self.processes.items():
            if process is None:
                continue

            try:
                process.poll()
                if process.poll() is None:
                    alive_processes.append(process_type)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                debug(f"Process {process_type} already dead or inaccessible")

        return alive_processes

    def stop_process(self, process_type: ProcessType):
        if process_type.value in self.process_mem.processes:
            self.process_mem.processes.remove(process_type.value)
        elif process_type.name in self.process_mem.processes:
            self.process_mem.processes.remove(process_type.name)
        process = self.processes.get(process_type)
        if process:
            info(f"Stopping process {process_type}")

            # Kill child processes first (to prevent zombie processes)
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    debug(f"Killing child process {child.pid}")
                    child.terminate()  # Try terminate first
                gone, alive = psutil.wait_procs(children, timeout=2)
                for child in alive:
                    debug(f"Force killing stubborn child process {child.pid}")
                    child.kill()  # Force kill if still alive

                # Now terminate the main process
                process.terminate()  # Try terminate first
                process.wait(timeout=2)  # Wait for process to exit

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                debug(f"Process {process_type} already dead or inaccessible")

            process.kill()

            del self.processes[process_type]
            info(f"Process {process_type} stopped successfully")
            self.save_process_mem()

    def save_process_mem(self):
        try:
            with open(self.last_processes_file, "w") as f:
                json.dump({"processes": self.process_mem.processes}, f)
        except (OSError, IOError) as e:
            warning(f"Failed to save processes to {self.last_processes_file}: {e}")

    def abort_all_processes(self):
        info("Start Abort!")
        # Create a copy of the processes dictionary to avoid modification during iteration
        processes_to_abort = list(self.processes.keys())
        for process_type in processes_to_abort:
            self.stop_process(process_type)

        info("Aborted Successfully!")

    async def monitor_process(self, process_type: ProcessType):
        timer = 0
        while True:
            if process_type not in self.processes:
                timer += 1
                if timer > 10:
                    warning(
                        f"Process {process_type} is not in the processes dictionary, skipping..."
                    )
                    break

                await asyncio.sleep(1)
                continue

            process = self.processes.get(process_type)
            timer = 0

            if process is None or process.poll() is not None:
                warning(f"Process {process_type} is dead, restarting...")
                self.processes[process_type] = start_process(
                    process_type, self.config_path
                )

            await asyncio.sleep(1)
