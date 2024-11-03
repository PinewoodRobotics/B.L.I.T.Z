from typing import Dict
from log import log_error, log_info

main_required = ["cameras", "image-input-topic", "image-output-topic"]

autobahn_required = [
    "internal-sub-port",
    "internal-pub-port",
]

camera_required = [
    "dist-coeff",
    "camera-matrix",
]


class Autobahn:
    def __init__(self, config):
        check_config(config, autobahn_required, "autobahn")
        self.internal_sub_port = config["internal-sub-port"]
        self.internal_pub_port = config["internal-pub-port"]


class Camera:
    def __init__(self, config):
        check_config(config, camera_required, "camera")
        self.camera_matrix: list[list[float]] = config["camera-matrix"]
        self.dist_coeff: list[list[float]] = config["dist-coeff"]


class Config:
    def __init__(self, config):
        self.autobahn = Autobahn(config["autobahn"])
        log_info("Config Resolver", "Autobahn Config loaded!")

        config = config["camera-feed-cleaner"]
        check_config(config, main_required, "main")
        log_info("Config Resolver", "Main Config loaded!")

        self.cameras: Dict[str, Camera] = {}
        self.input_topic = config["image-input-topic"]
        self.output_topic = config["image-output-topic"]
        for camera in config["cameras"]:
            self.cameras[camera] = Camera(config[camera])
        log_info("Config Resolver", "Camera Configs loaded!")


def check_config(config, required, submodule_name):
    for key in required:
        if key not in config:
            log_error("Config Resolver", f"Missing {key} in {submodule_name} config.")
            print()
            raise Exception()
