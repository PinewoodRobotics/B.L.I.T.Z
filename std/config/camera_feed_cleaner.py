from std.config_util import check_config

required_keys = ["cameras", "image-input-topic", "image-output-topic"]
required_keys_camera = ["dist-coeff", "camera-matrix"]


class CameraConfig:
    def __init__(self, config: dict):
        check_config(config, required_keys_camera, "CameraConfig")
        self.dist_coeff = config["dist-coeff"]
        self.camera_matrix = config["camera-matrix"]


class CameraFeedCleanerConfig:
    def __init__(self, config: dict):
        check_config(config, required_keys, "CameraFeedCleanerConfig")
        self.cameras = config["cameras"]
        self.image_input_topic = config["image-input-topic"]
        self.image_output_topic = config["image-output-topic"]
