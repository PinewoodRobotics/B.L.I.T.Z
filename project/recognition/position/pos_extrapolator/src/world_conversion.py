import time

import numpy as np
from project.common.config_class.filters.kalman_filter_config import MeasurementType
from project.common.config_class.pos_extrapolator import (
    ImuConfig,
    OdomConfig,
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
from filter import FilterStrategy
from filters.kalman import (
    KalmanFilterStrategy,
)


class WorldConversion:
    def __init__(
        self,
        filter_strategy: FilterStrategy,
        tag_configs: dict[str, TagPositionConfig] | None = None,
        imu_configs: list[ImuConfig] | None = None,
        odometry_config: list[OdomConfig] | None = None,
    ):
        self.filter_strategy = filter_strategy
        self.tag_configs = tag_configs
        self.imu_configs = imu_configs
        self.odometry_config = odometry_config
        self.last_timestamps = {}

    def insert_data(self, data: AprilTags | Imu | Odometry):
        if isinstance(self.filter_strategy, KalmanFilterStrategy):
            current_time = time.time()
            if str(type(data)) not in self.last_timestamps:
                self.last_timestamps[str(type(data))] = current_time

            self.filter_strategy.update_state_transition_matrix_5_5(
                current_time - self.last_timestamps[str(type(data))]
            )

            self.last_timestamps[str(type(data))] = current_time

            self.filter_strategy.predict()

        if isinstance(data, AprilTags):
            self._insert_april_tags(data)
        elif isinstance(data, Imu):
            self._insert_imu(data)
        elif isinstance(data, Odometry):
            self._insert_odometry(data)

    def get_position(self) -> list[float]:
        return self.filter_strategy.get_filtered_data()

    def get_confidence(self) -> float:
        return self.filter_strategy.get_confidence()

    def _insert_april_tags(self, data: AprilTags):
        if self.tag_configs is None:
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
            world_transform = get_world_pos(T_in_camera, tag_config.transformation)
            translation_component, rotation_component = (
                get_translation_rotation_components(world_transform)
            )

            # Extract yaw angle from rotation matrix (rotation around y-axis)
            # For a y-up coordinate system, use arctan2(r31, r33)
            # Since we have y-down, we negate the result
            rotation = -np.arctan2(rotation_component[2, 0], rotation_component[2, 2])
            print(rotation)

            self.filter_strategy.filter_data(
                [
                    translation_component[0],
                    translation_component[2],
                    0,
                    0,
                    rotation,
                ],
                MeasurementType.APRIL_TAG,
            )

    def _insert_imu(self, data: Imu):
        if self.imu_configs is None:
            raise ValueError("Imu configs are not set")

        imu_config = None
        for imu_config in self.imu_configs:
            if imu_config.name == data.imu_id:
                imu_config = imu_config
                break
        else:
            # raise ValueError(f"Imu config for {data.imu_id} not found")
            return

        self.filter_strategy.filter_data(
            [
                data.position.position.x - imu_config.imu_local_position[0],
                data.position.position.y - imu_config.imu_local_position[1],
                data.velocity.x,
                data.velocity.y,
                np.arctan2(data.position.direction.x, data.position.direction.y)
                - imu_config.imu_yaw_offset,
            ],
            MeasurementType.IMU,
        )

    def _insert_odometry(self, data: Odometry):
        if self.odometry_config is None:
            raise ValueError("Odometry config is not set")

        odom_config = self.odometry_config[0]

        self.filter_strategy.filter_data(
            [
                data.position.position.y - odom_config.odom_local_position[0],
                data.position.position.x - odom_config.odom_local_position[1],
                data.velocity.y,
                data.velocity.x,
                np.arctan2(data.position.direction.x, data.position.direction.y)
                - odom_config.odom_yaw_offset,
            ],
            MeasurementType.ODOMETRY,
        )

        self.last_timestamps[type(data)] = data.timestamp
