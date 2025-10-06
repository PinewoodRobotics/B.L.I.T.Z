import argparse
import asyncio
from logging import info
import os

from flask import Flask, request, jsonify

from backend.deployment.util import CommonModule
from backend.python.common.debug.logger import LogLevel, error, init_logging, success
from autobahn_client.client import Autobahn
from autobahn_client.util import Address
from backend.python.common.config import from_file
from backend.python.common.util.system import (
    BasicSystemConfig,
    get_local_ip,
    get_system_name,
    load_basic_system_config,
)
from watchdog.discovery import enable_discovery
from watchdog.helper import process_watcher, setup_ping_pong
from watchdog.monitor import ProcessMonitor
from backend.generated.thrift.config.ttypes import Config

app = Flask(__name__)

config_path = ""  # note: this should never be used because the config is set in the basic system config
processes_ran_path = "config/processes.json"

config: Config | None = None
basic_system_config: BasicSystemConfig | None = None
process_monitor: ProcessMonitor | None = None
zeroconf = None
system_name = ""


@app.route("/set/config", methods=["POST"])
def set_config():
    global config
    data = request.get_json()
    if "config" not in data:
        return jsonify({"status": "error", "message": "Missing config"}), 400

    config_data = data["config"].replace("\\n", "").replace("\n", "")

    with open(config_path, "w") as f:
        f.write(config_data)

    config = from_file(config_path)

    return jsonify({"status": "success"})


@app.route("/start/process", methods=["POST"])
def start():
    data = request.get_json()
    if config is None:
        return jsonify({"status": "error", "message": "Config not set"}), 400
    if process_monitor is None:
        return (
            jsonify({"status": "error", "message": "Process monitor not initialized"}),
            500,
        )
    if "process_types" not in data:
        return jsonify({"status": "error", "message": "Missing process_types"}), 400

    process_names = [str(p) for p in data["process_types"]]

    for process_name in process_names:
        success(f"Starting process: {process_name}")
        process_monitor.start_and_monitor_process(process_name)

    return jsonify({"status": "success"})


@app.route("/stop/process", methods=["POST"])
def stop():
    data = request.get_json()
    if config is None:
        return jsonify({"status": "error", "message": "Config not set"}), 400
    if process_monitor is None:
        return (
            jsonify({"status": "error", "message": "Process monitor not initialized"}),
            500,
        )
    if "process_types" not in data:
        return jsonify({"status": "error", "message": "Missing process_types"}), 400

    process_names = [str(p) for p in data["process_types"]]

    for process_name in process_names:
        success(f"Stopping process: {process_name}")
        process_monitor.stop_process(process_name)

    return jsonify({"status": "success"})


@app.route("/get/system/status", methods=["GET"])
def get_system_info():
    if process_monitor is None:
        return (
            jsonify({"status": "error", "message": "Process monitor not initialized"}),
            500,
        )

    active_processes = process_monitor.ping_processes_and_get_alive()
    return jsonify(
        {
            "status": "success",
            "system_info": system_name,
            "active_processes": active_processes,
            "config_set": config is not None,
        }
    )


async def main():
    global config_path, process_monitor, system_name, basic_system_config

    try:
        basic_system_config = load_basic_system_config()
    except FileNotFoundError:
        error("Basic system config not found, exiting.")
        return

    config_path = basic_system_config.config_path
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            f.write("")

    system_name = get_system_name()

    process_monitor = ProcessMonitor(processes_ran_path, config_path)
    process_monitor.set_event_loop(asyncio.get_running_loop())

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
        system_pub_topic=basic_system_config.logging.global_log_pub_topic,
        autobahn=autobahn_server,
    )

    success("Watchdog started!")

    await setup_ping_pong(autobahn_server, system_name)

    _ = asyncio.create_task(process_watcher(basic_system_config))
    success("Process watcher started!")

    process_monitor._restore_processes_from_memory()

    _ = await asyncio.to_thread(enable_discovery)
    success("Discovery enabled!")

    _ = await asyncio.to_thread(
        app.run,
        host=basic_system_config.watchdog.host,
        port=basic_system_config.watchdog.port,
        debug=False,
    )
    success("Flask app started!")


def cli_main():
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
