from std.config_util import check_config

required_keys = [
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

required_keys_message = ["post-camera-input-topic", "post-camera-output-topic"]

required_keys_camera = [
    "focal-length-x",
    "focal-length-y",
    "center-x",
    "center-y",
    "name",
]


class AprilDetectionMessageConfig:
    def __init__(self, config: dict):
        check_config(config, required_keys_message, "AprilDetectionMessageConfig")
        self.post_camera_input_topic = config["post-camera-input-topic"]
        self.post_camera_output_topic = config["post-camera-output-topic"]


class CameraConfig:
    def __init__(self, config: dict):
        check_config(config, required_keys_camera, "CameraConfig")
        self.focal_length_x = config["focal-length-x"]
        self.focal_length_y = config["focal-length-y"]
        self.center_x = config["center-x"]
        self.center_y = config["center-y"]
        self.name = config["name"]


class AprilDetectionConfig:
    def __init__(self, config: dict):
        check_config(config, required_keys, "AprilDetectionConfig")
        self.cameras = config["cameras"]
        self.tag_size = config["tag-size"]
        self.family = config["family"]
        self.nthreads = config["nthreads"]
        self.quad_decimate = config["quad_decimate"]
        self.quad_sigma = config["quad_sigma"]
        self.refine_edges = config["refine_edges"]
        self.decode_sharpening = config["decode_sharpening"]
        self.searchpath = config["searchpath"]
        self.debug = config["debug"]

        self.message = AprilDetectionMessageConfig(config["message"])
        self.cameras = [CameraConfig(camera) for camera in config["cameras"]]
