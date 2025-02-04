import argparse
import asyncio
import base64
import cv2
from flask_cors import CORS
from flask import Flask, jsonify, request
import toml
import threading
import pyapriltags
from config.main_config import (
    MainAppConfig,
    MainBackendConfig,
)
from module.camera_calibrator_apriltag import (
    CameraCalibratorApriltag,
    CameraCalibratorApriltagRunner,
)
from schema.update_config import UpdateConfig
from schema.update_calibration_params import (
    RemoveImage,
    UpdateCalibrationParams,
)
from module.module_thread import ModuleThread
from module.streamer import Camera, Streamer
from schema.update_mode import Mode, UpdateMode
from module.camera_calibrator_checkerboard import (
    CameraCalibratorCheckerboard,
    CameraCalibratorCheckerboardRunner,
)

# Configure logging

app = Flask(__name__)
CORS(app)

parser = argparse.ArgumentParser()
parser.add_argument("--main_config", type=str)
parser.add_argument("--app_config", type=str)

vals = parser.parse_args()
main_config = MainBackendConfig(toml.load(vals.main_config))
app_config = MainAppConfig.model_validate_json(open(vals.app_config).read())

current_mode = Mode.VIDEO

current_mode_run_thread: ModuleThread | None = None

camera = Camera(app_config.camera.camera_port)
streamer = Streamer(
    main_config.stream_hosting_port,
    camera,
    app_config.transformation,
    pyapriltags.Detector(
        "tag36h11",
        2,
    ),
)

camera_calibrator = CameraCalibratorCheckerboard(app_config.calibration.checkerboard)
camera_calibrator_apriltag = CameraCalibratorApriltag(
    app_config.calibration.checkerboard,
    "tag36h11",
    2,
)


@app.route("/get_saved_transformation_config", methods=["GET"])
def get_saved_transformation_config():
    return jsonify(app_config.transformation.model_dump())


@app.route("/get_calibration_data", methods=["GET"])
def get_calibration_data():
    if current_mode_run_thread is not None and (
        isinstance(current_mode_run_thread, CameraCalibratorCheckerboardRunner)
        or isinstance(current_mode_run_thread, CameraCalibratorApriltagRunner)
    ):
        data = current_mode_run_thread.calibrate_camera()
        if data is None:
            return jsonify({"error": "No calibration data available"})

        toml_string = toml.dumps(
            {
                "camera_matrix": data[0].tolist(),
                "dist_coeffs": data[1].tolist(),
            }
        )

        return jsonify(
            {
                "toml_string": toml_string,
            }
        )
    else:
        return jsonify({"error": "No calibration data available"})


@app.route("/update_calibration", methods=["POST"])
def update_calibration():
    print("Updating calibration")

    json = UpdateCalibrationParams(**request.get_json())
    app_config.calibration.checkerboard.update_config(json)

    app_config.save(vals.app_config)
    return "OK"


def pick_image_checkerboard(result):
    if result is None:
        return jsonify({"error": "No image picked"})
    else:
        _, buffer = cv2.imencode(".jpg", result[0][0])
        img_base64 = base64.b64encode(buffer).decode("utf-8")

        print(result[1])

        return jsonify(
            {
                "image": f"{img_base64}",
                "image_id": result[1],
            }
        )


@app.route("/update_settings", methods=["POST"])
def update_settings():
    json = UpdateConfig.model_validate(request.get_json())
    print(request.get_json())
    app_config.transformation.update_config(json)
    app_config.save(vals.app_config)
    return "OK"


@app.route("/pick_image", methods=["POST"])
def pick_image():
    global current_mode_run_thread
    if current_mode_run_thread is not None and (
        isinstance(current_mode_run_thread, CameraCalibratorCheckerboardRunner)
        or isinstance(current_mode_run_thread, CameraCalibratorApriltagRunner)
    ):
        return pick_image_checkerboard(current_mode_run_thread.pick_current_image())

    return jsonify({"error": "No image picked"})


@app.route("/remove_image", methods=["POST"])
def remove_image():
    json = RemoveImage.model_validate(request.get_json())

    if current_mode_run_thread is not None and (
        isinstance(current_mode_run_thread, CameraCalibratorCheckerboardRunner)
        or isinstance(current_mode_run_thread, CameraCalibratorApriltagRunner)
    ):
        current_mode_run_thread.remove_image(json.image_id)

    return "OK"


@app.route("/update_mode", methods=["POST"])
def update_mode():
    global current_mode_run_thread
    global streamer
    if current_mode_run_thread is not None:
        current_mode_run_thread.stop()
        current_mode_run_thread.join()

    json = UpdateMode(**request.get_json())
    print("Updating mode", json.new_mode)
    if json.new_mode == Mode.CHECKERBOARD.value or json.new_mode == Mode.APRILTAG.value:
        streamer.set_no_read_mode(True)
        camera.set_frame_lock(True)
        if json.new_mode == Mode.CHECKERBOARD.value:
            current_mode_run_thread = CameraCalibratorCheckerboardRunner(
                camera, camera_calibrator
            )
        else:
            current_mode_run_thread = CameraCalibratorApriltagRunner(
                camera, camera_calibrator_apriltag
            )

        current_mode_run_thread.start()
    elif json.new_mode == Mode.VIDEO.value:
        print("Updating mode to video")
        current_mode_run_thread = None
        streamer.set_no_read_mode(False)
        camera.set_frame_lock(False)
        streamer.set_no_read_mode(False)

    return "OK"


if __name__ == "__main__":
    print("Starting streamer")
    threading.Thread(target=asyncio.run, args=(streamer.start(),)).start()
    print("Starting app")
    app.run(
        host="127.0.0.1",
        port=main_config.main_hosting_port,
        debug=True,
        use_reloader=False,
    )
