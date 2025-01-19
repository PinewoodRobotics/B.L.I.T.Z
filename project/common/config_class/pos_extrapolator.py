from enum import Enum
from typing import Dict, Any, List
from project.common.config_class.config_template import ConfigTemplate

required_keys = [
    "cameras-to-analyze",
    "tag-position-config",
    "tag-confidence-threshold",
    "position-extrapolation-method",
]
required_keys_message = ["post-tag-input-topic", "post-robot-position-output-topic"]


class PositionExtrapolationMethod(Enum):
    AVERAGE_POSITION = "average-position"
    WEIGHTED_AVERAGE_POSITION = "weighted-average-position"
    MEDIAN_POSITION = "median-position"
    TREND_LINE_CENTER = "trend-line-center"
    KALMAN_LINEAR_FILTER = "kalman-linear-filter"


class PosExtrapolatorMessageConfig(ConfigTemplate):
    def __init__(self, config: Dict[str, str]) -> None:
        self.check_config(config, required_keys_message, "PosExtrapolatorMessageConfig")
        self.post_tag_input_topic = config["post-tag-input-topic"]
        self.post_robot_position_output_topic = config[
            "post-robot-position-output-topic"
        ]


class PosExtrapolatorConfig(ConfigTemplate):
    def __init__(self, config: Dict[str, Any]) -> None:
        self.check_config(config, required_keys, "PosExtrapolatorConfig")
        self.cameras_to_analyze = config["cameras-to-analyze"]

        tag_position_config = config["tag-position-config"]
        self.tag_position_config_file = tag_position_config["tag-position-config-file"]
        self.config_in_use = tag_position_config["config-in-use"]

        self.tag_confidence_threshold: float = config["tag-confidence-threshold"]
        self.position_extrapolation_method: PositionExtrapolationMethod = config[
            "position-extrapolation-method"
        ]

        self.message = PosExtrapolatorMessageConfig(config["message"])
