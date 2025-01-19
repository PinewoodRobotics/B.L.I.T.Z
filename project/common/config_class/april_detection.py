from typing import Any, List, Dict
from project.common.config_class.config_template import ConfigTemplate

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
    "post-camera-output-topic",
    "post-tag-output-topic",
]

required_keys_camera: List[str] = [
    "focal-length-x",
    "focal-length-y",
    "center-x",
    "center-y",
    "name",
]


class AprilDetectionMessageConfig(ConfigTemplate):
    post_camera_output_topic: str
    post_tag_output_topic: str

    def __init__(self, config: Dict[str, str]) -> None:
        self.check_config(config, required_keys_message, "AprilDetectionMessageConfig")
        self.post_camera_output_topic = config["post-camera-output-topic"]
        self.post_tag_output_topic = config["post-tag-output-topic"]


class AprilDetectionConfig(ConfigTemplate):
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

    def __init__(self, config: Dict[str, Any]) -> None:
        self.check_config(config, required_keys, "AprilDetectionConfig")
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
