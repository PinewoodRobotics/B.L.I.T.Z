from flask import current_app, request, jsonify
from typing import cast

from watchdog.monitor import ProcessMonitor
from .blueprint import bp


def _prep_for_validation(config_base64: str) -> str:
    filtered = "".join(c for c in config_base64 if c.isalnum() or c in "+/=")
    return filtered


@bp.route("/set/config", methods=["POST"])
def set_config():
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
    config_base64 = data.get("config_base64", None)
    if not isinstance(config_base64, str):
        return (
            jsonify({"status": "error", "message": "Missing or invalid parameters."}),
            400,
        )

    cfg = cast(dict[str, object], current_app.config)
    b64_obj = cfg.get("B64_CONFIG_FILE", None)
    b64_config_file = b64_obj if isinstance(b64_obj, str) else ""
    if not b64_config_file:
        return (
            jsonify(
                {"status": "error", "message": "Config path not initialized on app"}
            ),
            500,
        )
    with open(b64_config_file, "w") as f:
        _ = f.write(_prep_for_validation(config_base64))

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

    process_monitor.refresh_config()

    return jsonify({"status": "success"}), 200
