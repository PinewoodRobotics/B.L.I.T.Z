import asyncio
from typing import Awaitable, Callable, Dict, List
import subprocess
from project.autobahn.autobahn_python.autobahn import Autobahn
from project.autobahn.autobahn_python.util import Address
from project.watchdog.process_starter import start_process, start_process_make
from generated.Startup_pb2 import (
    MessageRetrievalConfirmation,
    ProcessType,
    StartupMessage,
)

CONFIG_PATH = "config/"
AUTOBAHN_RETRY_THRESHOLD = 2


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

    async def monitor_process(self, process_type: ProcessType):
        while True:
            process = self.processes.get(process_type)
            if not process:
                break

            return_code = process.poll()
            if return_code is not None:
                print(f"Process {process_type} exited with code {return_code}")
                new_process = start_process(process_type, CONFIG_PATH)
                if new_process:
                    self.processes[process_type] = new_process
                    print(f"Restarted process {process_type}")
                else:
                    print(f"Failed to restart process {process_type}")

            await asyncio.sleep(1)


async def check_autobahn_connection(
    autobahn_server: Autobahn, config_input: Callable[[bytes], Awaitable[None]]
):
    connected = False
    while not connected:
        for _ in range(AUTOBAHN_RETRY_THRESHOLD):
            try:
                await autobahn_server.begin()
                connected = True
            except Exception as e:
                print(f"Error connecting to Autobahn: {str(e)}")
                await asyncio.sleep(1)

        if connected:
            break

        start_process_make("autobahn")
    print("Autobahn connected")

    await autobahn_server.subscribe("config", config_input)


async def main():
    autobahn_server = Autobahn(Address("localhost", 8080))
    process_monitor = ProcessMonitor()

    async def config_input(data: bytes):
        startup_message = StartupMessage()
        startup_message.ParseFromString(data)

        with open(CONFIG_PATH + "config.json", "w") as f:
            f.write(startup_message.json_config)

        for process_type in startup_message.py_tasks:
            await process_monitor.start_and_monitor_process(process_type, CONFIG_PATH)

        await autobahn_server.publish(
            "watchdog/message_retrieval_confirmation",
            MessageRetrievalConfirmation(received=True).SerializeToString(),
        )

    await check_autobahn_connection(autobahn_server, config_input)

    while True:
        try:
            await autobahn_server.ping()
        except Exception as e:
            print(f"Error pinging Autobahn: {str(e)}")
            await check_autobahn_connection(autobahn_server, config_input)

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
