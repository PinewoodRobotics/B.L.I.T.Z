import os
import cv2
from matplotlib import pyplot as plt
import toml
import argparse
import zmq
from ultralytics import YOLO

from args import parse_args
from config import Config
from log import log_info
from message.Image import Box, DetectImage, ImageRecognitionOutput

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"


def open_config():
    with open("config.toml", "r") as file:
        config = toml.load(file)

    if config.get("main_config_path") and os.path.exists(config["main_config_path"]):
        with open(config["main_config_path"], "r") as file:
            log_info("Main Thread", "Using config file: " + config["main_config_path"])
            config = toml.load(file)
    else:
        log_info("Main Thread", "Using default config file!")

    return config


def reset_config():
    global config
    log_info("Main Thread", "Resetting config...")
    config = Config(open_config())


def initiate_pub_sub(config: Config):
    context = zmq.Context()

    internal_pub_socket = context.socket(zmq.PUB)
    internal_pub_socket.connect(f"tcp://localhost:{config.autobahn.internal_pub_port}")

    internal_sub_socket = context.socket(zmq.SUB)
    internal_sub_socket.connect(f"tcp://localhost:{config.autobahn.internal_sub_port}")
    internal_sub_socket.setsockopt_string(zmq.SUBSCRIBE, config.image_input_topic)

    return internal_pub_socket, internal_sub_socket


def name_from_number(model: YOLO, number: int):
    return model.names[number]


def run(config: Config, pub, sub, model: YOLO):
    log_info("Main Thread", "Starting inference processing...")

    poller = zmq.Poller()
    poller.register(sub, zmq.POLLIN)

    log_info("Main Thread", "Ready.")
    while True:
        socks = dict(poller.poll())

        if sub not in socks:
            continue

        message = sub.recv_string()[len(config.image_input_topic) :]
        image = DetectImage.from_json(message).decode_image()
        results = model.predict(source=image)

        result = ImageRecognitionOutput(
            [
                Box(
                    name_from_number(model, int(detection.cls[0].item())),
                    detection.conf[0].item(),
                    detection.xyxy[0].tolist(),
                )
                for detection in results[0].boxes
            ]
        )

        pub.send_string(f"{config.image_output_topic}{result.to_json()}")


def train(config: Config, model: YOLO):
    log_info("Main Thread", "Starting training...")

    model.train(
        data=config.trainer.data_yaml_path,
        epochs=config.trainer.epochs,
        imgsz=config.trainer.imgsz,
        name=config.trainer.name,
        batch=config.trainer.batch_size,
        device=config.device,
    )


if __name__ == "__main__":
    config = Config(open_config())
    training_mode_enabled = False if parse_args().train == "false" else True

    model = YOLO(config.model)
    if config.device != "":
        model.to(config.device)

    if training_mode_enabled:
        train(config, model)
    else:
        run(config, *initiate_pub_sub(config), model)
