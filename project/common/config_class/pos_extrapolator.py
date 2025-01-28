from enum import Enum
import os
from typing import Dict, Any, List

import numpy as np
from pydantic import BaseModel, computed_field
from project.common.config_class.config_template import ConfigTemplate
from project.common.util.math import (
    create_transformation_matrix,
    make_transformation_matrix,
)

required_keys = [
    "cameras-to-analyze",
    "imu-to-analyze",
    "tag-position-config",
    "tag-confidence-threshold",
    "position-extrapolation-method",
    "global-position-odometry",
    "imu",
]
required_keys_message = [
    "post-tag-input-topic",
    "post-odometry-input-topic",
    "post-imu-input-topic",
    "post-robot-position-output-topic",
]

required_keys_imu = ["global-position", "local-position"]


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
        self.post_odometry_input_topic = config["post-odometry-input-topic"]
        self.post_imu_input_topic = config["post-imu-input-topic"]
        self.post_robot_position_output_topic = config[
            "post-robot-position-output-topic"
        ]


class PosExtrapolatorConfig(ConfigTemplate):
    def __init__(self, config: Dict[str, Any]) -> None:
        self.check_config(config, required_keys, "PosExtrapolatorConfig")
        self.cameras_to_analyze = config["cameras-to-analyze"]
        self.imu_to_analyze = config["imu-to-analyze"]

        tag_position_config = config["tag-position-config"]
        self.tag_position_config_folder = tag_position_config[
            "tag-position-config-folder"
        ]

        self.config_in_use = tag_position_config["config-in-use"]

        tag_pos_files = os.listdir(self.tag_position_config_folder)
        config_file = None
        for file in tag_pos_files:
            if os.path.splitext(file)[0] == self.config_in_use:
                config_file = os.path.join(self.tag_position_config_folder, file)
                break

        if config_file is None:
            raise ValueError(
                f"Config file {self.config_in_use} not found in {self.tag_position_config_folder}"
            )

        with open(config_file) as f:
            tag_pos_config = AprilTagGlobalPosConfig.model_validate_json(f.read())
            self.tag_configs = tag_pos_config

        self.tag_confidence_threshold: float = config["tag-confidence-threshold"]
        self.position_extrapolation_method: PositionExtrapolationMethod = config[
            "position-extrapolation-method"
        ]

        self.message = PosExtrapolatorMessageConfig(config["message"])

        self.odometry_global_position = config["global-position-odometry"]
        imus = config["imu-to-analyze"]
        self.imu_configs = []
        for imu in imus:
            self.imu_configs.append(ImuConfig(config[imu]))


class ImuConfig(ConfigTemplate):
    def __init__(self, config: Dict[str, Any]) -> None:
        self.check_config(config, required_keys_imu, "ImuConfig")
        self.imu_global_position = config["global-position"]
        self.imu_local_position = config["local-position"]


class TagPositionConfig(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    x: float
    y: float
    z: float
    direction_vector: list[float]

    @computed_field
    @property
    def transformation(self) -> np.ndarray:
        return make_transformation_matrix(
            np.array([self.x, self.y, self.z]),
            np.array([-x for x in self.direction_vector]),
        )


class AprilTagGlobalPosConfig(BaseModel):
    config: Dict[str, TagPositionConfig]

    def __getitem__(self, key: str) -> TagPositionConfig:
        return self.config[key]
