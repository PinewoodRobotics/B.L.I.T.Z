from dataclasses import dataclass
import math
import numpy as np
from blitz.common.util.math import (
    create_transformation_matrix,
    from_float_list,
    get_np_from_matrix,
    get_np_from_vector,
    get_robot_in_world,
    get_translation_rotation_components,
    make_transformation_matrix_p_d,
)
from blitz.generated.proto.python.sensor.apriltags_pb2 import AprilTagData
from blitz.generated.proto.python.sensor.imu_pb2 import ImuData
from blitz.generated.proto.python.sensor.odometry_pb2 import OdometryData
from blitz.generated.thrift.config.common.ttypes import Point3
from blitz.generated.thrift.config.kalman_filter.ttypes import KalmanFilterSensorType
from blitz.generated.thrift.config.pos_extrapolator.ttypes import ImuConfig, OdomConfig
from blitz.pos_extrapolator.data_prep import (
    ConfigProvider,
    DataPreparer,
    DataPreparerManager,
    KalmanFilterInput,
)
from blitz.pos_extrapolator.position_extrapolator import PositionExtrapolator


@dataclass
class AprilTagConfig:
    tags_in_world: dict[int, Point3]
    cameras_in_robot: dict[str, Point3]
    use_imu_rotation: bool


class AprilTagDataPreparerConfig(ConfigProvider[AprilTagConfig]):
    def __init__(self, config: AprilTagConfig):
        self.config = config

    def get_config(self) -> AprilTagConfig:
        return self.config


@DataPreparerManager.register(proto_type=AprilTagData)
class AprilTagDataPreparer(DataPreparer[AprilTagData, AprilTagDataPreparerConfig]):
    def __init__(self, config: AprilTagDataPreparerConfig):
        super().__init__(config)
        self.config = config

    def get_data_type(self) -> type[AprilTagData]:
        return AprilTagData

    def get_avg_pose(self, input_list: list[list[float]]) -> np.ndarray:
        # TODO: potential bug here as we might want to do something more sophisticated here rather than just averaging
        return np.array(
            [
                np.mean([input[0] for input in input_list]),
                np.mean([input[1] for input in input_list]),
                np.mean([input[4] for input in input_list]),
            ]
        )

    def prepare_input(
        self, data: AprilTagData, sensor_id: str, x: np.ndarray | None = None
    ) -> KalmanFilterInput:
        if data.WhichOneof("data") == "raw_tags":
            raise ValueError("Tags are not in processed format")

        config = self.config.get_config()
        tags_in_world = config.tags_in_world
        cameras_in_robot = config.cameras_in_robot
        use_imu_rotation = config.use_imu_rotation

        input_list = []
        for tag in data.world_tags.tags:
            tag_id = tag.id
            if tag_id not in tags_in_world:
                continue

            T_camera_in_robot = create_transformation_matrix(
                rotation_matrix=get_np_from_matrix(
                    cameras_in_robot[sensor_id].rotation
                ),
                translation_vector=get_np_from_vector(
                    cameras_in_robot[sensor_id].position
                ),
            )
            T_tag_in_world = create_transformation_matrix(
                rotation_matrix=get_np_from_matrix(tags_in_world[tag_id].rotation),
                translation_vector=get_np_from_vector(tags_in_world[tag_id].position),
            )

            tag_in_camera_rotation = (
                PositionExtrapolator.CAMERA_OUTPUT_TO_ROBOT_ROTATION
                @ from_float_list(list(tag.pose_R), 3, 3)
                @ PositionExtrapolator.CAMERA_OUTPUT_TO_ROBOT_ROTATION.T
            )
            tag_in_camera_pose = (
                PositionExtrapolator.CAMERA_OUTPUT_TO_ROBOT_ROTATION
                @ np.array(tag.pose_t)
            )
            T_tag_in_camera = create_transformation_matrix(
                rotation_matrix=tag_in_camera_rotation,
                translation_vector=tag_in_camera_pose,
            )

            # render_pose, render_rotation = get_translation_rotation_components(
            #    T_tag_in_camera
            # )

            R_robot_rotation_world = None
            if use_imu_rotation and x is not None:
                R_robot_rotation_world = make_transformation_matrix_p_d(
                    position=np.array([0, 0, 0]),
                    direction_vector=np.array([x[4], x[5], 0]),
                )[:3, :3]

            render_pose, render_rotation = get_translation_rotation_components(
                get_robot_in_world(
                    T_tag_in_camera=T_tag_in_camera,
                    T_camera_in_robot=T_camera_in_robot,
                    T_tag_in_world=T_tag_in_world,
                    R_robot_rotation_world=R_robot_rotation_world,
                )
            )

            render_direction_vector = render_rotation[0:3, 0]
            # rotation_angle_rad = np.arctan2( <- correct rotation theta angle
            #    render_direction_vector[1], render_direction_vector[0]
            # )

            input_list.append(
                [
                    render_pose[0],
                    render_pose[1],
                    render_direction_vector[1],
                    render_direction_vector[0],
                ],
            )

        return KalmanFilterInput(
            input_list=self.get_avg_pose(input_list),
            sensor_id=sensor_id,
            sensor_type=KalmanFilterSensorType.APRIL_TAG,
            non_used_indices=[2, 3],
        )
