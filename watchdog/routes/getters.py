from flask import Blueprint, current_app, request, jsonify
from watchdog.monitor import ProcessMonitor
from typing import cast


GETTERS_BP = Blueprint("getter_routes", __name__)


@GETTERS_BP.route("/get/system/status", methods=["GET"])
def get_system_info():
    process_monitor = current_app.extensions.get("process_monitor", None)
    if not isinstance(process_monitor, ProcessMonitor):
        return (
            jsonify({"status": "error", "message": "Process monitor not initialized"}),
            500,
        )

    active_processes = process_monitor.ping_processes_and_get_alive()
    possible_processes: list[str] = process_monitor.get_possible_processes()
    cfg = cast(dict[str, object], current_app.config)
    system_name_obj = cfg.get("SYSTEM_NAME", None)
    system_name = system_name_obj if isinstance(system_name_obj, str) else ""

    return (
        jsonify(
            {
                "status": "success",
                "system_info": system_name,
                "active_processes": active_processes,
                "possible_processes": possible_processes,
                "config_set": process_monitor.is_config_exists,
            }
        ),
        200,
    )
