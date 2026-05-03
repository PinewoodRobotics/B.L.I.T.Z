import asyncio
import os
import threading

from flask import Flask

from watchdog.routes.getters import GETTERS_BP
from watchdog.routes.setters import SETTERS_BP
from watchdog.util.logger import LogLevel, error, init_logging, success
from autobahn_client.client import Autobahn
from autobahn_client.util import Address
from watchdog.util.system import (
    get_system_name,
    load_basic_system_config,
    WatchdogSystemConfig,
)
from watchdog.discovery import enable_discovery
from watchdog.helper import process_watcher, setup_ping_pong
from watchdog.monitor import ProcessMonitor

app = Flask(__name__)
app.register_blueprint(GETTERS_BP)
app.register_blueprint(SETTERS_BP)
process_monitor: ProcessMonitor | None = None

try:
    SYSTEM_CONFIG: WatchdogSystemConfig = load_basic_system_config()
    SYSTEM_NAME: str = get_system_name()
except FileNotFoundError:
    error("Basic system config or system name not found, exiting.")
    exit(1)

MANAGED_PROCESS_STATE_FILE = SYSTEM_CONFIG.watchdog_api.managed_process_state_file
DESIRED_CONFIG_BASE64_FILE = SYSTEM_CONFIG.desired_config_base64_path
app.config["SYSTEM_NAME"] = SYSTEM_NAME
app.config["DESIRED_CONFIG_BASE64_FILE"] = DESIRED_CONFIG_BASE64_FILE


async def main():
    global SYSTEM_CONFIG, SYSTEM_NAME, MANAGED_PROCESS_STATE_FILE, DESIRED_CONFIG_BASE64_FILE
    global process_monitor

    if not os.path.exists(DESIRED_CONFIG_BASE64_FILE):
        os.makedirs(os.path.dirname(DESIRED_CONFIG_BASE64_FILE), exist_ok=True)
        with open(DESIRED_CONFIG_BASE64_FILE, "w") as f:
            _ = f.write("")

    autobahn_server = Autobahn(
        Address(
            SYSTEM_CONFIG.autobahn_connection.host,
            SYSTEM_CONFIG.autobahn_connection.port,
        )
    )
    _ = await autobahn_server.begin()

    process_monitor = ProcessMonitor(
        MANAGED_PROCESS_STATE_FILE,
        DESIRED_CONFIG_BASE64_FILE,
        asyncio.get_running_loop(),
    )
    app.extensions["process_monitor"] = process_monitor

    init_logging(
        "WATCHDOG",
        LogLevel(SYSTEM_CONFIG.logging.default_log_level),
        system_pub_topic=SYSTEM_CONFIG.logging.log_publish_topic,
        autobahn=autobahn_server,
        system_name=SYSTEM_NAME,
    )

    success("Watchdog started!")

    await setup_ping_pong(autobahn_server, SYSTEM_NAME)

    _ = asyncio.create_task(process_watcher(SYSTEM_CONFIG))
    success("Process watcher started!")

    discovery_thread = threading.Thread(target=enable_discovery, daemon=True)
    discovery_thread.start()
    success("Discovery enabled!")

    flask_thread = threading.Thread(
        target=app.run,
        kwargs={
            "host": SYSTEM_CONFIG.watchdog_api.api_host,
            "port": SYSTEM_CONFIG.watchdog_api.api_port,
            "debug": False,
        },
        daemon=True,
    )
    flask_thread.start()
    success("Flask app started!")

    await asyncio.sleep(1)

    process_monitor._restore_processes_from_memory()

    _ = await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
