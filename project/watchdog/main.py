import asyncio
import subprocess
import sys
from typing import Dict, List

from flask import Flask, jsonify
import psutil

from generated.proto.python.WatchDogMessage_pb2 import (
    AbortMessage,
    MessageRetrievalConfirmation,
    ProcessType,
    StartupMessage,
)
from generated.proto.python.status.PiStatus_pb2 import PiProcess, PiStatus
from generated.thrift.config.ttypes import Config
from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address
from project.common.config import from_file
from project.common.util.system import get_system_name, get_top_10_processes
from project.watchdog.helper import process_watcher
from project.watchdog.monitor import ProcessMonitor
from project.watchdog.process_starter import start_process

CONFIG_PATH = "config/config.json"


async def main():
    autobahn_server = Autobahn(Address("localhost", 8080))
    process_monitor = ProcessMonitor(CONFIG_PATH)
    await autobahn_server.begin()

    config: Config | None = None

    async def config_input(data: bytes):
        nonlocal config

        startup_message = StartupMessage()
        startup_message.ParseFromString(data)

        with open(CONFIG_PATH, "w") as f:
            f.write(startup_message.json_config)

        config = from_file(CONFIG_PATH)

        await autobahn_server.publish(
            config.watchdog.confirmation_topic,
            MessageRetrievalConfirmation(received=True).SerializeToString(),
        )

        if startup_message.abort_previous:
            print("Aborting previous processes")
            process_monitor.abort_all_processes()

        for process_type in startup_message.py_tasks:
            print("Starting process " + str(process_type))
            await process_monitor.start_and_monitor_process(process_type, CONFIG_PATH)

    await autobahn_server.subscribe(get_system_name() + "/config", config_input)

    await process_watcher(config, autobahn_server)


if __name__ == "__main__":
    asyncio.run(main())
