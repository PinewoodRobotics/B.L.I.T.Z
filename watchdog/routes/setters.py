from flask import Blueprint, current_app, request, jsonify
from watchdog.monitor import ProcessMonitor
from typing import cast


SETTERS_BP = Blueprint("setter_routes", __name__)


@SETTERS_BP.route("/set/config", methods=["POST"])
def set_config():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("config_base64"), str):
        return (
            jsonify({"status": "error", "message": "Missing or invalid parameters"}),
            400,
        )

    b64_config_file: str = cast(str, current_app.config.get("B64_CONFIG_FILE"))

    config_base64: str = cast(str, data.get("config_base64"))
    filtered = "".join(c for c in config_base64 if c.isalnum() or c in "+/=")
    with open(b64_config_file, "w") as f:
        f.write(filtered)

    monitor = current_app.extensions.get("process_monitor")
    if not isinstance(monitor, ProcessMonitor):
        return (
            jsonify({"status": "error", "message": "Process monitor not initialized"}),
            500,
        )

    monitor.refresh_config()
    return jsonify({"status": "success"}), 200


@SETTERS_BP.route("/start/process", methods=["POST"])
def start_process():
    data = request.get_json(silent=True)
    process_types = data.get("process_types") if isinstance(data, dict) else None
    if not isinstance(process_types, list) or not all(
        isinstance(p, str) for p in process_types
    ):
        return (
            jsonify({"status": "error", "message": "Missing or invalid parameters"}),
            400,
        )

    monitor = current_app.extensions.get("process_monitor")
    if not isinstance(monitor, ProcessMonitor):
        return (
            jsonify({"status": "error", "message": "Process monitor not initialized"}),
            500,
        )

    if not monitor.is_config_exists:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Config not set. Please set the config and try again",
                }
            ),
            400,
        )

    for process_name in process_types:
        monitor.start_and_monitor_process(process_name)

    return jsonify({"status": "success"}), 200


@SETTERS_BP.route("/stop/all/processes", methods=["POST"])
def stop_all_processes():
    process_monitor = current_app.extensions.get("process_monitor", None)
    if not isinstance(process_monitor, ProcessMonitor):
        return (
            jsonify({"status": "error", "message": "Process monitor not initialized"}),
            500,
        )

    process_monitor.abort_all_processes()
    return jsonify({"status": "success"}), 200


@SETTERS_BP.route("/stop/process", methods=["POST"])
def stop_process():
    data_raw = request.get_json(silent=True)
    if not isinstance(data_raw, dict):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Missing or invalid parameters.",
                }
            ),
            400,
        )

    data = cast(dict[str, object], data_raw)
    process_types_obj = data.get("process_types", None)
    if not isinstance(process_types_obj, list):
        return (
            jsonify({"status": "error", "message": "Missing or invalid parameters."}),
            400,
        )

    process_types_obj = cast(list[object], process_types_obj)
    process_types = [x for x in process_types_obj if isinstance(x, str)]
    if len(process_types) != len(process_types_obj):
        return (
            jsonify({"status": "error", "message": "Missing or invalid parameters."}),
            400,
        )

    process_monitor: ProcessMonitor = cast(
        ProcessMonitor, current_app.extensions.get("process_monitor")
    )

    for process_name in process_types:
        process_monitor.stop_process(process_name)

    return jsonify({"status": "success"}), 200


@SETTERS_BP.route("/set/processes", methods=["POST"])
def set_processes():
    data = request.get_json(silent=True)
    process_types = data.get("process_types") if isinstance(data, dict) else None
    if not isinstance(process_types, list) or not all(
        isinstance(p, str) for p in process_types
    ):
        return (
            jsonify({"status": "error", "message": "Missing or invalid parameters"}),
            400,
        )

    monitor = current_app.extensions.get("process_monitor")
    if not isinstance(monitor, ProcessMonitor):
        return (
            jsonify({"status": "error", "message": "Process monitor not initialized"}),
            500,
        )

    if not monitor.is_config_exists:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Config not set. Please set the config and try again",
                }
            ),
            400,
        )

    monitor.set_processes(process_types)

    return jsonify({"status": "success"}), 200
