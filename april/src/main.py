import os
import cv2
from flask import Flask, request
import pyapriltags
import requests
import toml
from colorama import Fore, Style, init

from config import Config
from message.DetectTag import DetectImage, PositionData, PostOutput, Tag


def log_info(message):
    print("[April Main Thread]", Fore.CYAN, message, Style.RESET_ALL)


def open_config():
    with open("config.toml", "r") as file:
        config = toml.load(file)

    if config["main_config_path"] is not None and os.path.exists(
        config["main_config_path"]
    ):
        with open(config["main_config_path"], "r") as file:
            log_info("Using config file: " + config["main_config_path"])
            config = toml.load(file)
    else:
        log_info("Using default config file!")

    return config["april-detection"]


config = Config(open_config())
server = Flask(__name__)
detector = pyapriltags.Detector(
    families=str(config.main.family),
    nthreads=config.main.nthreads,
    quad_decimate=config.main.quad_decimate,
    quad_sigma=config.main.quad_sigma,
    refine_edges=config.main.refine_edges,
    decode_sharpening=config.main.decode_sharpening,
    debug=0 if config.main.debug == False else 1,
    searchpath=config.main.searchpath,
)

try:
    requests.post(
        "http://localhost:" + str(config.message.sending_port) + "/subscribe",
        json={
            "topic": config.message.post_camera_input_topic,
            "post_url": "http://localhost:"
            + str(config.message.listening_port)
            + "/process",
        },
    )
except Exception as e:
    log_info("Failed to subscribe to message topic: " + str(e))
    exit(1)


@server.route("/process", methods=["POST"])
def on_message():
    if config.main.debug:
        log_info("Received message! Processing it...")

    message = DetectImage.from_json(request.json)
    if message.camera not in config.cameras:
        log_info(f"Unknown camera: {message.camera}")

    image = message.decode_image()
    if not message.is_grayscale:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    out = detector.detect(
        image,
        estimate_tag_pose=True,
        camera_params=(
            config.cameras[message.camera].focal_length_x,
            config.cameras[message.camera].focal_length_y,
            config.cameras[message.camera].center_x,
            config.cameras[message.camera].center_y,
        ),
        tag_size=config.main.tag_size,
    )

    out_msg = PostOutput(message.camera, [])
    for tag in out:
        out_msg.add_tag(Tag(tag, PositionData(tag)))

    requests.post(
        "http://localhost:" + str(config.message.sending_port) + "/post",
        json={
            "topic": config.message.post_camera_output_topic,
            "data": out_msg.to_json(),
        },
    )

    return "Processed message successfully", 200


server.run(host="localhost", port=config.message.listening_port)
