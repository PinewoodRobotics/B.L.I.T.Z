from colorama import Fore, Style
from typing import Dict

required_config_main = [
    "cameras",
    "tag-size",
    "family",
    "nthreads",
    "quad_decimate",
    "quad_sigma",
    "refine_edges",
    "decode_sharpening",
    "searchpath",
    "debug",
]

required_config_camera = [
    "focal-length-x",
    "focal-length-y",
    "center-x",
    "center-y",
]

required_config_message = [
    "listening-port",
    "sending-port",
    "post-camera-input-topic",
    "post-camera-output-topic",
]


class Config:
    def __init__(self, config):
        if not self.check_toml_config(config):
            return

        self.main = Main(config)
        log_info("Found main config.")
        self.cameras: Dict[str, Camera] = self.get_camera_configs(config)
        log_info("Found camera configs.")
        self.message = Message(config["message"])
        log_info("Found message config.")

    def get_camera_configs(self, config):
        cameras = {}
        for camera in self.main.cameras:
            camera = Camera(config[camera], camera)
            cameras[camera.name] = camera

        return cameras

    def check_toml_config(self, config):
        if config is None:
            return False
        for key in required_config_main:
            if key not in config:
                log_error(f"Missing config: {key}.")
                return False

        for camera in config["cameras"]:
            if not camera in config:
                log_error(f"Missing config for camera: '{camera}'.")
                return False

            if not self.check_camera_config(config[camera], camera):
                return False

        if not self.check_message_config(config["message"]):
            return False

        return True

    def check_camera_config(self, config, camera_name):
        if config is None:
            return False

        for key in required_config_camera:
            if key not in config:
                log_error(f"Missing config for '{camera_name}': {key}.")
                return False
        return True

    def check_message_config(self, config):
        if config is None:
            return False

        for key in required_config_message:
            if key not in config:
                log_error(f"Missing config for message config: '{key}'.")
                return False
        return True


class Main:
    def __init__(self, config):
        self.cameras = config["cameras"]
        self.tag_size = config["tag-size"]
        self.family = config["family"]
        self.nthreads = config["nthreads"]
        self.quad_decimate = config["quad_decimate"]
        self.quad_sigma = config["quad_sigma"]
        self.refine_edges = config["refine_edges"]
        self.decode_sharpening = config["decode_sharpening"]
        self.searchpath = config["searchpath"]
        self.debug = False if config["debug"] == 0 else True


class Message:
    def __init__(self, config):
        self.listening_port = config["listening-port"]
        self.sending_port = config["sending-port"]
        self.post_camera_input_topic = config["post-camera-input-topic"]
        self.post_camera_output_topic = config["post-camera-output-topic"]


class Camera:
    def __init__(self, config, name):
        self.focal_length_x = config["focal-length-x"]
        self.focal_length_y = config["focal-length-y"]
        self.center_x = config["center-x"]
        self.center_y = config["center-y"]

        self.name = config["name"] if config["name"] else name


def log_error(message):
    print(Fore.RED + message)


def log_info(message):
    log(Fore.BLUE + message)


def log(message):
    print("[April Config Resolver]", message, Style.RESET_ALL)
