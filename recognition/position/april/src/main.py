import os
import threading
import time
import cv2
import zmq
import pyapriltags
import toml
from colorama import Fore, Style
from config import Config
from message.DetectTag import DetectImage, NamedDetection, PositionData, PostOutput, Tag


def log_info(message):
    print("[April Main Thread]", Fore.CYAN, message, Style.RESET_ALL)


def open_config():
    with open("config.toml", "r") as file:
        config = toml.load(file)

    if config.get("main_config_path") and os.path.exists(config["main_config_path"]):
        with open(config["main_config_path"], "r") as file:
            log_info("Using config file: " + config["main_config_path"])
            config = toml.load(file)
    else:
        log_info("Using default config file!")

    return config


def get_detector(config: Config):
    return pyapriltags.Detector(
        families=str(config.main.family),
        nthreads=config.main.nthreads,
        quad_decimate=config.main.quad_decimate,
        quad_sigma=config.main.quad_sigma,
        refine_edges=config.main.refine_edges,
        decode_sharpening=config.main.decode_sharpening,
        debug=0,
        searchpath=config.main.searchpath,
    )


def reset_config():
    global config
    global detector
    log_info("Resetting config...")
    config = Config(open_config())
    detector = get_detector(config)


def input_thread():
    global user_input
    while True:
        user_input = input()
        if user_input == "reload":
            reset_config()


thread = threading.Thread(target=input_thread, daemon=True)
thread.start()

user_input = None
config = Config(open_config())
detector = get_detector(config)

context = zmq.Context()

internal_pub_socket = context.socket(zmq.PUB)
internal_pub_socket.connect(f"tcp://localhost:{config.autobahn.internal_pub_port}")

internal_sub_socket = context.socket(zmq.SUB)
internal_sub_socket.connect(f"tcp://localhost:{config.autobahn.internal_sub_port}")
internal_sub_socket.setsockopt_string(
    zmq.SUBSCRIBE, config.message.post_camera_input_topic
)

poller = zmq.Poller()
poller.register(internal_sub_socket, zmq.POLLIN)

time.sleep(1)
log_info("Ready!")

while True:
    socks = dict(poller.poll())

    if internal_sub_socket not in socks:
        continue

    message = internal_sub_socket.recv_string()[
        len(config.message.post_camera_input_topic) :
    ]

    if config.main.debug:
        log_info("Received message: " + message)

    message_content = DetectImage.from_json(message)
    image = message_content.decode_image()

    if not message_content.is_grayscale:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    camera_config = config.cameras[message_content.camera_name]
    tags = detector.detect(
        image,
        estimate_tag_pose=True,
        camera_params=[
            camera_config.focal_length_x,
            camera_config.focal_length_y,
            camera_config.center_x,
            camera_config.center_y,
        ],
        tag_size=config.main.tag_size,
    )

    output = PostOutput(message_content.camera_name, [])
    for tag in tags:
        output.add_tag(
            Tag(
                NamedDetection(
                    tag.tag_family,
                    tag.tag_id,
                    tag.hamming,
                    tag.decision_margin,
                    tag.homography.tolist(),
                    tag.center.tolist(),
                    [corner.tolist() for corner in tag.corners],
                    tag.pose_R.tolist() if tag.pose_R is not None else None,
                    tag.pose_t.tolist() if tag.pose_t is not None else None,
                    tag.pose_err,
                    tag.tag_size,
                ),
                PositionData(tag),
            )
        )

    internal_pub_socket.send_string(
        config.message.post_camera_output_topic + output.to_json()
    )
