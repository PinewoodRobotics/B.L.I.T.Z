import time

import numpy as np

from generated.AprilTag_pb2 import AprilTags
from generated.Imu_pb2 import Imu
from generated.Odometry_pb2 import Odometry
from project.common.config_class.filters.kalman_filter_config import MeasurementType
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
    get_robot_in_world,
)
from project.pos_extrapolator.src.kalman_filter import KalmanFilterStrategy


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
        self.camera_output_to_robot_rotation = np.array(
            [
                [0, 0, 1],
                [-1, 0, 0],
                [0, -1, 0],
            ]
        )

    def insert_data(self, data: AprilTags | Imu | Odometry):
        self.predict_step()

        if isinstance(data, AprilTags):
            self.sensor_completions[0] = True
            self._insert_april_tags(data, data.camera_name)
        elif isinstance(data, Imu) and self.config.enable_imu:
            self.sensor_completions[1] = True
            self._insert_imu(data)
        elif isinstance(data, Odometry) and self.config.enable_odom:
            self.sensor_completions[2] = True
            self._insert_odometry(data)

    def predict_step(self):
        """
        Note: this will take the timestamp of the last predict point.
        """

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
        # print(self.tag_configs)
        if (
            self.tag_configs is None
            or self.camera_configs is None
            or camera_name not in self.camera_configs
        ):
            print(
                f"Tag configs: {self.tag_configs}, Camera configs: {self.camera_configs}, Camera name: {camera_name}"
            )
            raise ValueError("Tag configs are not set")

        cur_state = self.filter_strategy.get_state()

        for tag in data.tags:
            tag_id = str(tag.tag_id)
            if tag_id not in self.tag_configs:
                continue

            T_camera_in_robot = self.config.camera_configs[camera_name].transformation
            T_tag_in_world = self.config.tag_position_config[tag_id].transformation

            tag_in_camera_rotation = (
                self.camera_output_to_robot_rotation
                @ from_float_list(list(tag.pose_R), 3, 3)
                @ self.camera_output_to_robot_rotation.T
            )
            tag_in_camera_pose = self.camera_output_to_robot_rotation @ np.array(
                tag.pose_t
            )
            T_tag_in_camera = create_transformation_matrix(
                rotation_matrix=tag_in_camera_rotation,
                translation_vector=tag_in_camera_pose,
            )

            # render_pose, render_rotation = get_translation_rotation_components(
            #    T_tag_in_camera
            # )

            render_pose, render_rotation = get_translation_rotation_components(
                get_robot_in_world(
                    T_tag_in_camera=T_tag_in_camera,
                    T_camera_in_robot=T_camera_in_robot,  # const
                    T_tag_in_world=T_tag_in_world,  # const
                )
            )

            render_direction_vector = render_rotation[0:3, 0]
            rotation_angle_rad = np.arctan2(
                render_direction_vector[1], render_direction_vector[0]
            )

            print(
                [round(v * 10) for v in render_direction_vector],
                round(np.degrees(rotation_angle_rad)),
            )

            distance = tag.distance_to_camera
            noise_value = exponential_noise_scaling(distance)

            self.filter_strategy.insert_data(
                [
                    render_pose[0],
                    render_pose[1],
                    0,
                    0,
                    rotation_angle_rad,
                ],
                MeasurementType.APRIL_TAG,
                noise_value,
            )

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
                data.position.position.x,
                data.position.position.y,
                data.position.direction.x,
                data.position.direction.y,
                data.rotation_rads,
            ],
            MeasurementType.ODOMETRY,
            1,
        )


def exponential_noise_scaling(distance, a=0.03, b=0.3):
    return a * np.exp(b * abs(distance))


def distance2d(pos1: list[float], pos2: list[float]) -> float:
    return np.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)
