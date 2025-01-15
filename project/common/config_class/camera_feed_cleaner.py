import numpy as np
from project.common.config_class.config_template import ConfigTemplate

required_keys = ["cameras", "image-input-topic", "image-output-topic"]
required_keys_camera = ["dist-coeff", "camera-matrix"]


class CameraConfig(ConfigTemplate):
    def __init__(self, config: dict):
        self.check_config(config, required_keys_camera, "CameraConfig")
        self.dist_coeff = np.array(config["dist-coeff"])
        self.camera_matrix = np.array(config["camera-matrix"])


class CameraFeedCleanerConfig(ConfigTemplate):
    def __init__(self, config: dict):
        self.check_config(config, required_keys, "CameraFeedCleanerConfig")
        self.cameras = config["cameras"]
        self.image_input_topic = config["image-input-topic"]
        self.image_output_topic = config["image-output-topic"]
