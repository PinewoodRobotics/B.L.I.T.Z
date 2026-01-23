from flask import current_app, request, jsonify
from typing import cast
from watchdog.monitor import ProcessMonitor
from watchdog.util.logger import success
from .blueprint import bp


@bp.route("/start/process", methods=["POST"])
def start_process():
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

    process_monitor = current_app.extensions.get("process_monitor", None)

    if not isinstance(process_monitor, ProcessMonitor):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Process monitor not initialized just yet. Wait a bit and try again.",
                }
            ),
            500,
        )
    if not process_monitor.is_config_exists:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Config not set. Please set the config and try again.",
                }
            ),
            400,
        )

    for process_name in process_types:
        success(f"Starting process: {process_name}")
        process_monitor.start_and_monitor_process(process_name)

    return jsonify({"status": "success"}), 200
