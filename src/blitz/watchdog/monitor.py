import asyncio
import subprocess
from typing import Dict, List

import psutil

from blitz.watchdog.helper import ProcessType
from blitz.watchdog.process_starter import start_process


class ProcessMonitor:
    def __init__(self):
        self.processes: Dict[ProcessType, subprocess.Popen] = {}
        self.process_args: Dict[ProcessType, List[str]] = {}
        self.config_path: str | None = None

    def start_and_monitor_process(
        self,
        process_type: ProcessType,
    ):
        if self.config_path is None:
            raise ValueError("Config path not set")

        process = start_process(process_type, self.config_path)
        if process:
            self.processes[process_type] = process
            asyncio.create_task(self.monitor_process(process_type))

    def set_config_path(self, config_path: str):
        self.config_path = config_path

    def ping_processes_and_get_alive(self):
        alive_processes = []
        for process_type, process in self.processes.items():
            try:
                process.poll()
                if process.poll() is None:
                    alive_processes.append(process_type)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                print(f"Process {process_type} already dead or inaccessible")

        return alive_processes

    def stop_process(self, process_type: ProcessType):
        process = self.processes.get(process_type)
        if process:
            print(f"Stopping process {process_type}")

            # Kill child processes first (to prevent zombie processes)
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    print(f"Killing child process {child.pid}")
                    child.terminate()  # Try terminate first
                gone, alive = psutil.wait_procs(children, timeout=2)
                for child in alive:
                    print(f"Force killing stubborn child process {child.pid}")
                    child.kill()  # Force kill if still alive

                # Now terminate the main process
                process.terminate()  # Try terminate first
                process.wait(timeout=2)  # Wait for process to exit

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                print(f"Process {process_type} already dead or inaccessible")

            process.kill()

            del self.processes[process_type]
            print(f"Process {process_type} stopped successfully")

    def abort_all_processes(self):
        print("Start Abort!")
        # Create a copy of the processes dictionary to avoid modification during iteration
        processes_to_abort = list(self.processes.keys())
        for process_type in processes_to_abort:
            self.stop_process(process_type)

        print("Aborted Sucessfully!")

    async def monitor_process(self, process_type: ProcessType):
        while True:
            process = self.processes.get(process_type)
            if not process:
                break

            return_code = process.poll()
            if return_code is not None:
                print(f"Process {process_type} exited with code {return_code}")
                if self.config_path is None:
                    raise ValueError("Config path not set")

                new_process = start_process(process_type, self.config_path)
                if new_process:
                    self.processes[process_type] = new_process
                    print(f"Restarted process {process_type}")
                    break
                else:
                    print(f"Failed to restart process {process_type}")

            await asyncio.sleep(1)
