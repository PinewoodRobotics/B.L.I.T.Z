from enum import Enum
from typing import Dict, Any

import numpy as np
from pydantic import BaseModel
from project.common.util.math import (
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


class PosExtrapolatorMessageConfig(BaseModel):
    post_tag_input_topic: str
    post_odometry_input_topic: str
    post_imu_input_topic: str
    post_robot_position_output_topic: str

    @classmethod
    def validate_config(cls, config: Dict[str, str]) -> "PosExtrapolatorMessageConfig":
        for key in required_keys_message:
            if key not in config:
                raise ValueError(f"Missing required key: {key}")
        return cls(**config)


class PosExtrapolatorConfig(BaseModel):
    cameras_to_analyze: str
    imu_to_analyze: str
    tag_position_config_folder: str
    config_in_use: str
    tag_position_config: Dict[str, "TagPositionConfig"]
    tag_confidence_threshold: float
    position_extrapolation_method: PositionExtrapolationMethod
    message: PosExtrapolatorMessageConfig
    odometry_global_position: str
    imu_configs: Dict[str, "ImuConfig"]

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> "PosExtrapolatorConfig":
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required key: {key}")
        return cls(**config)


class ImuConfig(BaseModel):
    imu_global_position: str
    imu_local_position: str
    imu_yaw_offset: str

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> "ImuConfig":
        for key in required_keys_imu:
            if key not in config:
                raise ValueError(f"Missing required key: {key}")
        return cls(**config)


class TagPositionConfig(BaseModel):
    x: float
    y: float
    z: float
    direction_vector: list[float]

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
