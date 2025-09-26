import argparse
import asyncio
from logging import info
import os
import socket
import subprocess
import sys
import time
from typing import Dict, List

from flask import Flask, request, jsonify
import psutil
from zeroconf import ServiceInfo, Zeroconf

from blitz.common.debug.logger import LogLevel, error, init_logging, success
from autobahn_client.client import Autobahn
from autobahn_client.util import Address
from blitz.generated.thrift.config.ttypes import Config
from blitz.common.config import from_file
from blitz.common.util.system import (
    ProcessType,
    get_local_ip,
    get_system_name,
    load_basic_system_config,
)
from blitz.watchdog.helper import process_watcher
from blitz.watchdog.monitor import ProcessMonitor
from blitz.generated.proto.python.status.PiStatus_pb2 import Ping, Pong

app = Flask(__name__)

config_path = "system_data/snapshot_config.txt"
processes_run_path = "config/processes.json"

config: Config | None = None
process_monitor: ProcessMonitor | None = None
zeroconf = None
system_name = ""


@app.route("/set/config", methods=["POST"])
def set_config():
    global config
    data = request.get_json()
    if "config" not in data:
        return jsonify({"status": "error", "message": "Missing config"}), 400

    config_dir = os.path.dirname(config_path)
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)

    config_data = data["config"].replace("\\n", "").replace("\n", "")

    with open(config_path, "w") as f:
        f.write(config_data)

    config = from_file(config_path)

    if process_monitor is not None:
        process_monitor.set_config_path(config_path)

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

    process_types = []
    for process_type_str in data["process_types"]:
        try:
            process_type = ProcessType(process_type_str)
            process_types.append(process_type)
        except ValueError:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Invalid process type: {process_type_str}",
                    }
                ),
                400,
            )

    for process_type in process_types:
        success(f"Starting process: {process_type}")
        process_monitor.start_and_monitor_process(process_type)

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

    process_types = []
    for process_type_str in data["process_types"]:
        try:
            process_type = ProcessType(process_type_str)
            process_types.append(process_type)
        except ValueError:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Invalid process type: {process_type_str}",
                    }
                ),
                400,
            )

    for process_type in process_types:
        success(f"Stopping process: {process_type}")
        process_monitor.stop_process(process_type)

    return jsonify({"status": "success"})


@app.route("/get/system/status", methods=["GET"])
def get_system_info():
    if process_monitor is None:
        return (
            jsonify({"status": "error", "message": "Process monitor not initialized"}),
            500,
        )

    active_processes = process_monitor.get_active_processes()
    return jsonify(
        {
            "status": "success",
            "system_info": system_name,
            "active_processes": list(active_processes),
            "config_set": config is not None,
        }
    )


def enable_discovery():
    """
    Enables zeroconf discovery for the system.

    This allows other devices on the same network to discover this Pi.
    Uses the zeroconf protocol to broadcast the Pi's presence and details.
    """
    global zeroconf
    zeroconf = Zeroconf()

    hostname = socket.gethostname()
    local_ip = get_local_ip()
    if local_ip is None:
        error("No local IP found, cannot register service")
        return

    addr = socket.inet_aton(local_ip)

    _info = ServiceInfo(
        "_deploy._udp.local.",
        f"{hostname}._deploy._udp.local.",
        addresses=[addr],
        port=9999,
        properties={"id": hostname},
    )

    zeroconf.register_service(_info)
    success(f"Registered service {hostname} on {local_ip}")


async def setup_ping_pong(autobahn_server: Autobahn):
    async def ping_server(data: bytes):
        ping = Ping.FromString(data)
        pong = Pong(
            pi_name=system_name,
            timestamp_ms_received=int(time.time() * 1000),
            timestamp_ms_original=int(ping.timestamp),
        )

        await autobahn_server.publish("pi-pong", pong.SerializeToString())

    await autobahn_server.subscribe("pi-ping", ping_server)


async def main():
    global config_path, process_monitor, system_name

    basic_system_config = load_basic_system_config()
    config_path = basic_system_config.config_path
    system_name = get_system_name()

    event_loop = asyncio.get_running_loop()
    process_monitor = ProcessMonitor(processes_run_path, event_loop)
    if basic_system_config.config_path:
        process_monitor.set_config_path(basic_system_config.config_path)

    autobahn_server = Autobahn(
        Address(
            basic_system_config.autobahn.host,
            basic_system_config.autobahn.port,
        )
    )
    await autobahn_server.begin()
    await setup_ping_pong(autobahn_server)

    init_logging(
        "WATCHDOG",
        LogLevel(basic_system_config.logging.global_logging_level),
        system_pub_topic=basic_system_config.logging.global_log_pub_topic,
        autobahn=autobahn_server,
    )

    success("Watchdog started!")

    asyncio.create_task(process_watcher(basic_system_config))
    success("Process watcher started!")

    await asyncio.to_thread(enable_discovery)
    success("Discovery enabled!")

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
