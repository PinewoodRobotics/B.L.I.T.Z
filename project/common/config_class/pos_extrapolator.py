import numpy as np
from pydantic import BaseModel
from typing import Dict, List
from project.common.util.math import make_transformation_matrix_p_d
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
        return make_transformation_matrix_p_d(
            position=np.array(self.camera_robot_position),
            direction_vector=np.array(self.camera_robot_direction),
        )


class TagPositionConfig(BaseModel):
    x: float
    y: float
    z: float
    direction_vector: List[float]
    z_axis: List[float] | None = None

    @property
    def transformation(self) -> np.ndarray:
        return make_transformation_matrix_p_d(
            position=np.array([self.x, self.y, self.z]),
            # The convention: tag's direction vector sticks out of the FACE side of
            # the tag, i.e. TOWARDS the observer. But in the raw data returned by the
            # camera, it's assumed that it should stick out of the BACK side of the tag,
            # i.e. AWAY from the observer. So we do a -1 * correction in the beginning
            # and then assume that everywhere else, the tag's direction vector is
            # normal to its BACK (invisible) plane.
            direction_vector=-1 * np.array(self.direction_vector),
            z_axis=np.array(self.z_axis) if self.z_axis else np.array([0, 0, 1]),
        )


class PosExtrapolatorConfig(BaseModel):
    message_config: PosExtrapolatorMessageConfig
    tag_position_config: Dict[
        str, TagPositionConfig
    ]  # Matches `Record<string, Position3D>`
    tag_confidence_threshold: float

    april_tag_discard_distance: float

    enable_imu: bool
    enable_odom: bool
    enable_tags: bool

    odom_configs: OdomConfig
    imu_configs: Dict[str, ImuConfig]
    camera_configs: Dict[str, CameraConfig]

    kalman_filter: KalmanFilterConfig
