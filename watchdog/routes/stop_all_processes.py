from flask import current_app, request, jsonify
from watchdog.monitor import ProcessMonitor
from .blueprint import bp


@bp.route("/stop/all/processes", methods=["POST"])
def stop_all_processes():
    process_monitor = current_app.extensions.get("process_monitor", None)
    if not isinstance(process_monitor, ProcessMonitor):
        return (
            jsonify({"status": "error", "message": "Process monitor not initialized"}),
            500,
        )

    process_monitor.abort_all_processes()
    return jsonify({"status": "success"}), 200
