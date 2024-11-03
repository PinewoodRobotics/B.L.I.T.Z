import base64
import cv2
import toml
import zmq
import numpy as np

from config import Config
from log import log_info
from msg.Image import Image, ImageOutput


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
    internal_sub_socket.setsockopt_string(zmq.SUBSCRIBE, config.input_topic)

    return internal_pub_socket, internal_sub_socket


if __name__ == "__main__":
    config = Config(open_config())

    pub, sub = initiate_pub_sub(config)
    poller = zmq.Poller()
    poller.register(sub, zmq.POLLIN)

    while True:
        socks = dict(poller.poll())

        if sub not in socks:
            continue

        message = sub.recv_string()[len(config.input_topic) :]
        message_decoded = Image.from_json(message)

        if message_decoded.camera_name not in config.cameras:
            continue

        # Convert camera matrix and distortion coefficients to numpy arrays
        camera_matrix = np.array(
            config.cameras[message_decoded.camera_name].camera_matrix
        )
        dist_coeff = np.array(config.cameras[message_decoded.camera_name].dist_coeff)
        image = message_decoded.decode_image()
        height, width = image.shape[:2]

        new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
            camera_matrix,
            dist_coeff,
            (width, height),
            1,
            (width, height),
        )
        map1, map2 = cv2.initUndistortRectifyMap(
            camera_matrix,
            dist_coeff,
            None,
            new_camera_matrix,
            (width, height),
            cv2.CV_16SC2,
        )

        frame = cv2.remap(
            image,
            map1,
            map2,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )

        if message_decoded.do_cropping:
            # Define cropping percentages
            side_crop_percent = 0.2  # Crop 20% from each side
            top_bottom_crop_percent = 0.2  # Crop 20% from top and bottom

            # Calculate pixel values for cropping
            side_crop = int(width * side_crop_percent)
            top_bottom_crop = int(height * top_bottom_crop_percent)

            # Calculate crop boundaries
            x_start = side_crop
            x_end = width - side_crop
            y_start = top_bottom_crop
            y_end = height - top_bottom_crop

            # Apply cropping to frame
            frame = frame[y_start:y_end, x_start:x_end]

        _, encoded_image = cv2.imencode(".jpg", frame)
        encoded_base64 = base64.b64encode(encoded_image).decode("utf-8")
        pub.send_string(
            f"{config.output_topic}{ImageOutput(encoded_base64, message_decoded.camera_name).to_json()}",
        )
