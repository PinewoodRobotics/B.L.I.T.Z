import argparse
import asyncio
import subprocess
import sys
from typing import Dict, List

from flask import Flask, Request, jsonify
import psutil

from blitz.common.debug.logger import LogLevel, init_logging, success
from blitz.generated.proto.python.WatchDogMessage_pb2 import (
    MessageRetrievalConfirmation,
    StartupMessage,
)
from blitz.generated.thrift.config.ttypes import Config
from blitz.common.autobahn_python.autobahn import Autobahn
from blitz.common.autobahn_python.util import Address
from blitz.common.config import from_file
from blitz.common.util.system import get_system_name, load_basic_system_config
from blitz.watchdog.helper import ProcessType, process_watcher
from blitz.watchdog.monitor import ProcessMonitor

app = Flask(__name__)

CONFIG_PATH = "config/config.json"

config: Config | None = None
process_monitor = ProcessMonitor()


@app.route("/set/config", methods=["POST"])
def set_config(request: Request):
    global config
    data = request.get_json()
    if "config" not in data:
        return jsonify({"status": "error", "message": "Missing config"}), 400

    with open(CONFIG_PATH, "w") as f:
        f.write(data["config"])

    config = from_file(CONFIG_PATH)

    process_monitor.set_config_path(CONFIG_PATH)

    return jsonify({"status": "success"})


@app.route("/start/process", methods=["POST"])
def start(request: Request):
    data = request.get_json()
    if config is None:
        return jsonify({"status": "error", "message": "Config not set"}), 400
    if "process_type" not in data:
        return jsonify({"status": "error", "message": "Missing process type"}), 400
    if data["process_type"] not in ProcessType:
        return jsonify({"status": "error", "message": "Invalid process type"}), 400

    process_types = [
        ProcessType(process_type) for process_type in data["process_types"]
    ]
    for process_type in process_types:
        process_monitor.start_and_monitor_process(process_type)

    return jsonify({"status": "success"})


@app.route("/stop/process", methods=["POST"])
def stop(request: Request):
    data = request.get_json()
    if config is None:
        return jsonify({"status": "error", "message": "Config not set"}), 400
    if "process_type" not in data:
        return jsonify({"status": "error", "message": "Missing process type"}), 400
    if data["process_type"] not in ProcessType:
        return jsonify({"status": "error", "message": "Invalid process type"}), 400

    process_types = [
        ProcessType(process_type) for process_type in data["process_types"]
    ]
    for process_type in process_types:
        process_monitor.stop_process(process_type)

    return jsonify({"status": "success"})


async def main():
    basic_system_config = load_basic_system_config()

    autobahn_server = Autobahn(
        Address(
            basic_system_config.autobahn.host,
            basic_system_config.autobahn.port,
        )
    )
    await autobahn_server.begin()

    init_logging(
        "WATCHDOG",
        LogLevel(basic_system_config.logging.global_logging_level),
        basic_system_config.logging.global_log_pub_topic,
        autobahn_server,
    )

    success("Watchdog started!")

    asyncio.create_task(process_watcher(basic_system_config))
    success("Process watcher started!")

    await asyncio.to_thread(
        app.run,
        host=basic_system_config.watchdog.host,
        port=basic_system_config.watchdog.port,
        debug=False,
    )


def cli_main():
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
