import asyncio
import os
import threading
import importlib

from flask import Flask

from watchdog.util.logger import LogLevel, error, init_logging, success
from autobahn_client.client import Autobahn
from autobahn_client.util import Address
from watchdog.util.system import (
    BasicSystemConfig,
    get_system_name,
    load_basic_system_config,
)
from watchdog.discovery import enable_discovery
from watchdog.helper import process_watcher, setup_ping_pong
from watchdog.monitor import ProcessMonitor
from watchdog.routes.blueprint import bp as routes_bp

_ = importlib.import_module("watchdog.routes.get_status")
_ = importlib.import_module("watchdog.routes.set_config")
_ = importlib.import_module("watchdog.routes.start_process")
_ = importlib.import_module("watchdog.routes.stop_process")

app = Flask(__name__)
app.register_blueprint(routes_bp)
process_monitor: ProcessMonitor | None = None

try:
    BASIC_SYSTEM_CONFIG: BasicSystemConfig = load_basic_system_config()
    SYSTEM_NAME: str = get_system_name()
except FileNotFoundError:
    error("Basic system config or system name not found, exiting.")
    exit(1)

PROCESS_MEMORY_FILE = BASIC_SYSTEM_CONFIG.watchdog.process_memory_file
B64_CONFIG_FILE = BASIC_SYSTEM_CONFIG.config_path
app.config["SYSTEM_NAME"] = SYSTEM_NAME
app.config["B64_CONFIG_FILE"] = B64_CONFIG_FILE


async def main():
    global BASIC_SYSTEM_CONFIG, SYSTEM_NAME, PROCESS_MEMORY_FILE, B64_CONFIG_FILE
    global process_monitor

    if not os.path.exists(B64_CONFIG_FILE):
        os.makedirs(os.path.dirname(B64_CONFIG_FILE), exist_ok=True)
        with open(B64_CONFIG_FILE, "w") as f:
            _ = f.write("")

    autobahn_server = Autobahn(
        Address(
            BASIC_SYSTEM_CONFIG.autobahn.host,
            BASIC_SYSTEM_CONFIG.autobahn.port,
        )
    )
    _ = await autobahn_server.begin()

    process_monitor = ProcessMonitor(
        PROCESS_MEMORY_FILE, B64_CONFIG_FILE, asyncio.get_running_loop()
    )
    app.extensions["process_monitor"] = process_monitor

    init_logging(
        "WATCHDOG",
        LogLevel(BASIC_SYSTEM_CONFIG.logging.global_logging_level),
        system_pub_topic=BASIC_SYSTEM_CONFIG.logging.global_log_pub_topic,
        autobahn=autobahn_server,
        system_name=SYSTEM_NAME,
    )

    success("Watchdog started!")

    await setup_ping_pong(autobahn_server, SYSTEM_NAME)

    _ = asyncio.create_task(process_watcher(BASIC_SYSTEM_CONFIG))
    success("Process watcher started!")

    discovery_thread = threading.Thread(target=enable_discovery, daemon=True)
    discovery_thread.start()
    success("Discovery enabled!")

    flask_thread = threading.Thread(
        target=app.run,
        kwargs={
            "host": BASIC_SYSTEM_CONFIG.watchdog.host,
            "port": BASIC_SYSTEM_CONFIG.watchdog.port,
            "debug": False,
        },
        daemon=True,
    )
    flask_thread.start()
    success("Flask app started!")

    await asyncio.sleep(1)

    process_monitor._restore_processes_from_memory()

    _ = await asyncio.Event().wait()


def cli_main():
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
