import asyncio
import subprocess
import sys
from typing import Dict, List

import psutil

from generated.WatchDogMessage_pb2 import (AbortMessage,
                                           MessageRetrievalConfirmation,
                                           ProcessType, StartupMessage)
from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address
from project.common.config_class.name import get_system_name
from project.watchdog.process_starter import start_process

CONFIG_PATH = "config/config.json"
LOGGING = True


def log(message: str):
    global LOGGING
    if LOGGING:
        sys.stderr.write(message + "\n")


class ProcessMonitor:
    def __init__(self):
        self.processes: Dict[ProcessType, subprocess.Popen] = {}
        self.process_args: Dict[ProcessType, List[str]] = {}

    async def start_and_monitor_process(
        self,
        process_type: ProcessType,
        config_path: str,
    ):
        process = start_process(process_type, config_path)
        if process:
            self.processes[process_type] = process
            asyncio.create_task(self.monitor_process(process_type))


    def stop_process(self, process_type: ProcessType):
        process = self.processes.get(process_type)
        if process:
            log(f"Stopping process {process_type}")

            # Kill child processes first (to prevent zombie processes)
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    log(f"Killing child process {child.pid}")
                    child.terminate()  # Try terminate first
                gone, alive = psutil.wait_procs(children, timeout=2)
                for child in alive:
                    log(f"Force killing stubborn child process {child.pid}")
                    child.kill()  # Force kill if still alive

                # Now terminate the main process
                process.terminate()  # Try terminate first
                process.wait(timeout=2)  # Wait for process to exit

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                log(f"Process {process_type} already dead or inaccessible")

            
            process.kill()

            del self.processes[process_type]
            log(f"Process {process_type} stopped successfully")

    def abort_all_processes(self):
        log("Start Abort!")
        for process_type in self.processes:
            self.stop_process(process_type)
        
        log("Aborted Sucessfully!")
        
    async def monitor_process(self, process_type: ProcessType):
        while True:
            process = self.processes.get(process_type)
            if not process:
                break

            return_code = process.poll()
            if return_code is not None:
                log(f"Process {process_type} exited with code {return_code}")
                new_process = start_process(process_type, CONFIG_PATH)
                if new_process:
                    self.processes[process_type] = new_process
                    log(f"Restarted process {process_type}")
                    break
                else:
                    log(f"Failed to restart process {process_type}")

            await asyncio.sleep(1)


async def main():
    autobahn_server = Autobahn(Address("localhost", 8080))
    process_monitor = ProcessMonitor()
    await autobahn_server.begin()

    async def config_input(data: bytes):
        log("Received config")
        startup_message = StartupMessage()
        startup_message.ParseFromString(data)

        with open(CONFIG_PATH, "w") as f:
            f.write(startup_message.json_config)

        if startup_message.abort_previous:
            log("Aborting previous processes")
            process_monitor.abort_all_processes()

        for process_type in startup_message.py_tasks:
            log("Starting process " + str(process_type))
            await process_monitor.start_and_monitor_process(process_type, CONFIG_PATH)

        log("Sent out!")
        await autobahn_server.publish(
            get_system_name() + "/watchdog/message_retrieval_confirmation",
            MessageRetrievalConfirmation(received=True).SerializeToString(),
        )

    async def abort_input(data: bytes):
        abort_message = AbortMessage()
        abort_message.ParseFromString(data)
        log("Received abort")

        for process_type in abort_message.py_tasks:
            process_monitor.stop_process(process_type)

    await autobahn_server.subscribe("config", config_input)
    await autobahn_server.subscribe("abort", abort_input)

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    sys.stderr.write("This is an error message ;)\n")
    asyncio.run(main())
