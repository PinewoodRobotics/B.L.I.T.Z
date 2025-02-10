import numpy as np
from enum import Enum
from typing import Dict
from pydantic import BaseModel
from project.common.util.math import make_transformation_matrix
from project.common.config_class.filters.kalman_filter_config import KalmanFilterConfig


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


class ImuConfig(BaseModel):
    imu_global_position: list[float]
    imu_local_position: list[float]
    imu_yaw_offset: float
    max_r2_drift: float


class OdomConfig(BaseModel):
    odom_global_position: list[float]
    odom_local_position: list[float]
    odom_yaw_offset: float
    max_r2_drift: float


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


class PosExtrapolatorConfig(BaseModel):
    position_extrapolation_method: PositionExtrapolationMethod
    message_config: PosExtrapolatorMessageConfig

    tag_position_config: dict[str, TagPositionConfig]
    tag_confidence_threshold: float

    imu_configs: list[ImuConfig]
    odom_configs: list[OdomConfig]

    kalman_filter: KalmanFilterConfig


class AprilTagGlobalPosConfig(BaseModel):
    config: Dict[str, TagPositionConfig]

    def __getitem__(self, key: str) -> TagPositionConfig:
        return self.config[key]
