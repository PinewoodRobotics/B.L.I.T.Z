import argparse
import base64
import cv2
from flask_socketio import SocketIO, emit
from flask import Flask, request, jsonify
import toml

from config.config_util import get_config_data
from config.main_config import (
    MainAppConfig,
    MainBackendConfig,
)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

parser = argparse.ArgumentParser()
parser.add_argument("--main_config", type=str)
parser.add_argument("--app_config", type=str)

vals = parser.parse_args()
main_config = MainBackendConfig(toml.load(vals.main_config))


app_config = MainAppConfig(**get_config_data(vals.app_config))

camera = cv2.VideoCapture(app_config.camera.camera_port)


def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break

        _, buffer = cv2.imencode(".jpg", frame)
        frame_b64 = base64.b64encode(buffer).decode("utf-8")
        yield frame_b64


@socketio.on("request_frame")
def stream_video():
    for frame in generate_frames():
        emit("frame", {"data": frame}, broadcast=True)
