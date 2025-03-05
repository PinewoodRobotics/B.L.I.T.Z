import asyncio
import subprocess
from typing import Dict, List

from generated.WatchDogMessage_pb2 import AbortMessage, MessageRetrievalConfirmation, ProcessType, StartupMessage
from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address
from project.watchdog.process_starter import start_process

CONFIG_PATH = "config/"
LOGGING = True

def log(message: str):
    if LOGGING:
        print(message)


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
    
    async def stop_process(self, process_type: ProcessType):
        process = self.processes.get(process_type)
        if process:
            process.terminate()
            process.wait()

        del self.processes[process_type]
    
    async def abort_all_processes(self):
        for process_type in self.processes:
            await self.stop_process(process_type)

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
                else:
                    log(f"Failed to restart process {process_type}")

            await asyncio.sleep(1)


async def main():
    autobahn_server = Autobahn(Address("localhost", 8080))
    process_monitor = ProcessMonitor()

    async def config_input(data: bytes):
        log("Received config")
        startup_message = StartupMessage()
        startup_message.ParseFromString(data)

        with open(CONFIG_PATH + "config.json", "w") as f:
            f.write(startup_message.json_config)
            log("Wrote config to " + CONFIG_PATH + "config.json")
        
        if startup_message.abort_previous:
            log("Aborting previous processes")
            await process_monitor.abort_all_processes()

        for process_type in startup_message.py_tasks:
            log("Starting process " + str(process_type))
            await process_monitor.start_and_monitor_process(process_type, CONFIG_PATH)

        await autobahn_server.publish(
            "watchdog/message_retrieval_confirmation",
            MessageRetrievalConfirmation(received=True).SerializeToString(),
        )
    
    async def abort_input(data: bytes):
        abort_message = AbortMessage()
        abort_message.ParseFromString(data)
        log("Received abort")
        
        for process_type in abort_message.py_tasks:
            await process_monitor.stop_process(process_type)

    await autobahn_server.subscribe("config", config_input)
    await autobahn_server.subscribe("abort", abort_input)

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
