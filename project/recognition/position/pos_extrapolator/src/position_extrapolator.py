import time

import numpy as np
from project.common.config_class.filters.kalman_filter_config import (
    MeasurementType,
)
from project.common.config_class.pos_extrapolator import (
    CameraConfig,
    ImuConfig,
    OdomConfig,
    PosExtrapolatorConfig,
    TagPositionConfig,
)
from project.common.util.math import (
    create_transformation_matrix,
    from_float_list,
    get_translation_rotation_components,
    get_world_pos,
)
from generated.AprilTag_pb2 import AprilTags
from generated.Imu_pb2 import Imu
from generated.Odometry_pb2 import Odometry
from project.recognition.position.pos_extrapolator.src.kalman_filter import (
    KalmanFilterStrategy,
)


class PositionExtrapolator:
    def __init__(
        self,
        config: PosExtrapolatorConfig,
        filter_strategy: KalmanFilterStrategy,
        camera_configs: dict[str, CameraConfig] | None = None,
        tag_configs: dict[str, TagPositionConfig] | None = None,
        imu_configs: dict[str, ImuConfig] | None = None,
        odometry_config: OdomConfig | None = None,
    ):
        self.camera_configs = camera_configs
        self.config = config
        self.filter_strategy = filter_strategy
        self.tag_configs = tag_configs
        self.imu_configs = imu_configs
        self.odometry_config = odometry_config

        self.last_predict = time.time()
        self.sensor_completions: list[bool] = [True, False, False]

    def insert_data(self, data: AprilTags | Imu | Odometry):
        self.predict_step()

        if isinstance(data, AprilTags):
            self.sensor_completions[0] = True
            self._insert_april_tags(data, data.camera_name)
        elif isinstance(data, Imu):
            self.sensor_completions[1] = True
            self._insert_imu(data)
        elif isinstance(data, Odometry):
            self.sensor_completions[2] = True
            self._insert_odometry(data)

    def predict_step(self):
        """
        Note: this will take the timestamp of the last predict point.
        """

        if self.sensor_completions == [
            True,
            self.config.enable_imu,
            self.config.enable_odom,
        ]:
            self.filter_strategy.update_transformation_delta_t(
                time.time() - self.last_predict
            )
            self.filter_strategy.predict()
            self.last_predict = time.time()
            self.sensor_completions = [True, False, False]

    def get_position(self) -> list[float]:
        return self.filter_strategy.get_filtered_data()

    def get_confidence(self) -> float:
        return self.filter_strategy.get_confidence()

    def _insert_april_tags(self, data: AprilTags, camera_name: str):
        if (
            self.tag_configs is None
            or self.camera_configs is None
            or camera_name not in self.camera_configs
        ):
            print(
                f"Tag configs: {self.tag_configs}, Camera configs: {self.camera_configs}, Camera name: {camera_name}"
            )
            raise ValueError("Tag configs are not set")

        for tag in data.tags:
            if str(tag.tag_id) not in self.tag_configs:
                continue

            T_in_camera = create_transformation_matrix(
                from_float_list(list(tag.pose_R), 3, 3),
                np.array(
                    [
                        tag.pose_t[0],
                        tag.pose_t[1],
                        tag.pose_t[2],
                    ]
                ),
            )

            tag_config = self.tag_configs[str(tag.tag_id)]
            world_transform = get_world_pos(
                T_in_camera,
                self.camera_configs[camera_name].transformation,
                tag_config.transformation,
            )
            translation_component, rotation_component = (
                get_translation_rotation_components(world_transform)
            )

            # Extract yaw angle from rotation matrix (rotation around y-axis)
            # For a y-up coordinate system, use arctan2(r31, r33)
            # Since we have y-down, we negate the result
            rotation = -np.arctan2(rotation_component[2, 0], rotation_component[2, 2])
            distance = tag.distance_to_camera
            decision_margin = tag.decision_margin

            if distance <= 0.1:
                distance = 0.1

            if decision_margin <= 0.01:
                decision_margin = 0.01

            noise_value = (distance**2) + (1.0 / decision_margin)
            self.filter_strategy.insert_data(
                [
                    translation_component[0],
                    translation_component[2],
                    0,
                    0,
                    rotation,
                ],
                MeasurementType.APRIL_TAG,
                noise_value,
            )

    """
    class ImuConfig(BaseModel):
        use_rotation: bool
        use_position: bool
        use_velocity: bool

        imu_robot_position: List[float]
        imu_robot_rotation: List[float]
    """

    def _insert_imu(self, data: Imu):
        if self.imu_configs is None:
            raise ValueError("Imu configs are not set")

        imu_config = self.imu_configs[data.imu_id]
        _ = np.array(imu_config.imu_robot_position)
        _ = np.array(imu_config.imu_robot_direction_vector)

        self.filter_strategy.insert_data(
            [
                data.position.position.x,
                data.position.position.y,
                data.velocity.x,
                data.velocity.y,
                np.arctan2(data.position.direction.x, data.position.direction.y),
            ],
            MeasurementType.IMU,
            1,
        )

    def _insert_odometry(self, data: Odometry):
        if self.odometry_config is None:
            raise ValueError("Odometry config is not set")

        self.filter_strategy.insert_data(
            [
                data.position.position.y,
                data.position.position.x,
                data.position.direction.x,
                data.position.direction.y,
                data.rotation_rads,
            ],
            MeasurementType.ODOMETRY,
            1,
        )
