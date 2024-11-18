from project.common.config_util import check_config
from typing import Any, List, Dict

required_keys: List[str] = [
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

required_keys_message: List[str] = [
    "post-camera-input-topic",
    "post-camera-output-topic",
]

required_keys_camera: List[str] = [
    "focal-length-x",
    "focal-length-y",
    "center-x",
    "center-y",
    "name",
]


class AprilDetectionMessageConfig:
    post_camera_input_topic: str
    post_camera_output_topic: str

    def __init__(self, config: Dict[str, str]) -> None:
        check_config(config, required_keys_message, "AprilDetectionMessageConfig")
        self.post_camera_input_topic = config["post-camera-input-topic"]
        self.post_camera_output_topic = config["post-camera-output-topic"]


class CameraConfig:
    focal_length_x: float
    focal_length_y: float
    center_x: float
    center_y: float
    name: str

    def __init__(self, config: Dict[str, float | str]) -> None:
        check_config(config, required_keys_camera, "CameraConfig")
        self.focal_length_x = float(config["focal-length-x"])
        self.focal_length_y = float(config["focal-length-y"])
        self.center_x = float(config["center-x"])
        self.center_y = float(config["center-y"])
        self.name = str(config["name"])


class AprilDetectionConfig:
    tag_size: float
    family: str
    nthreads: int
    quad_decimate: float
    quad_sigma: float
    refine_edges: bool
    decode_sharpening: float
    searchpath: str
    debug: bool
    message: AprilDetectionMessageConfig
    cameras: Dict[str, CameraConfig]

    def __init__(self, config: Dict[str, Any]) -> None:
        check_config(config, required_keys, "AprilDetectionConfig")
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
        self.cameras: Dict[str, CameraConfig] = {}
        for camera in config["cameras"]:
            self.cameras[camera] = CameraConfig(config[camera])
