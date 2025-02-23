import numpy as np
from pydantic import BaseModel
from typing import Dict, List
from project.common.util.math import make_transformation_matrix
from project.common.config_class.filters.kalman_filter_config import KalmanFilterConfig


class PosExtrapolatorMessageConfig(BaseModel):
    post_tag_input_topic: str
    post_odometry_input_topic: str
    post_imu_input_topic: str
    post_robot_position_output_topic: str
    set_position: str  # Added to match TS


class ImuConfig(BaseModel):
    use_rotation: bool
    use_position: bool
    use_velocity: bool

    imu_robot_position: List[float]
    imu_robot_direction_vector: List[float]


class OdomConfig(BaseModel):
    use_position: bool
    use_rotation: bool

    odom_robot_position: List[float]  # 3D Vector
    odom_robot_rotation: List[float]  # 3D Vector


class CameraConfig(BaseModel):
    camera_robot_position: List[float]  # 3D Vector
    camera_robot_direction: List[float]  # 3D Vector

    @property
    def transformation(self) -> np.ndarray:
        return make_transformation_matrix(
            np.array(self.camera_robot_position),
            np.array([-x for x in self.camera_robot_direction]),
        )


class TagPositionConfig(BaseModel):
    x: float
    y: float
    z: float
    direction_vector: List[float]

    @property
    def transformation(self) -> np.ndarray:
        return make_transformation_matrix(
            np.array([self.x, self.y, self.z]),
            np.array([-x for x in self.direction_vector]),
        )


class PosExtrapolatorConfig(BaseModel):
    message_config: PosExtrapolatorMessageConfig
    tag_position_config: Dict[
        str, TagPositionConfig
    ]  # Matches `Record<string, Position3D>`
    tag_confidence_threshold: float

    enable_imu: bool
    enable_odom: bool
    enable_tags: bool

    odom_configs: OdomConfig
    imu_configs: Dict[str, ImuConfig]
    camera_configs: Dict[str, CameraConfig]

    kalman_filter: KalmanFilterConfig
