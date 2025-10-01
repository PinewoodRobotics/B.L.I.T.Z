from dataclasses import dataclass
import math
import numpy as np
from numpy.typing import NDArray
from blitz.common.util.math import (
    create_transformation_matrix,
    from_float_list,
    get_np_from_matrix,
    get_np_from_vector,
    get_robot_in_world,
    get_translation_rotation_components,
    make_3d_rotation_from_yaw,
    make_transformation_matrix_p_d,
    transform_matrix_to_size,
    transform_vector_to_size,
)
from blitz.generated.proto.python.sensor.apriltags_pb2 import AprilTagData
from blitz.generated.proto.python.sensor.imu_pb2 import ImuData
from blitz.generated.proto.python.sensor.odometry_pb2 import OdometryData
from blitz.generated.thrift.config.common.ttypes import Point3
from blitz.generated.thrift.config.kalman_filter.ttypes import KalmanFilterSensorType
from blitz.generated.thrift.config.pos_extrapolator.ttypes import (
    ImuConfig,
    OdomConfig,
    TagUseImuRotation,
)
from blitz.pos_extrapolator.data_prep import (
    ConfigProvider,
    DataPreparer,
    DataPreparerManager,
    ExtrapolationContext,
    KalmanFilterInput,
)
from blitz.pos_extrapolator.position_extrapolator import PositionExtrapolator


@dataclass
class AprilTagConfig:
    tags_in_world: dict[int, Point3]
    cameras_in_robot: dict[str, Point3]
    use_imu_rotation: TagUseImuRotation


class AprilTagDataPreparerConfig(ConfigProvider[AprilTagConfig]):
    def __init__(self, config: AprilTagConfig):
        self.config = config

    def get_config(self) -> AprilTagConfig:
        return self.config


@DataPreparerManager.register(proto_type=AprilTagData)
class AprilTagDataPreparer(DataPreparer[AprilTagData, AprilTagDataPreparerConfig]):
    def __init__(self, config: AprilTagDataPreparerConfig):
        super().__init__(config)
        self.config: AprilTagDataPreparerConfig = config

        conf = self.config.get_config()
        self.tags_in_world: dict[int, Point3] = conf.tags_in_world
        self.cameras_in_robot: dict[str, Point3] = conf.cameras_in_robot
        self.use_imu_rotation: TagUseImuRotation = conf.use_imu_rotation

    def get_data_type(self) -> type[AprilTagData]:
        return AprilTagData

    def get_avg_pose(self, input_list: list[list[float]]) -> NDArray[np.float64]:
        output: list[float] = []
        for i in range(len(input_list[0])):
            output.append(
                np.mean(
                    [input[i] for input in input_list]
                )  # pyright: ignore[reportArgumentType]
            )  # pyright: ignore[reportArgumentType]

        return np.array(output)

    def get_used_indices(self) -> list[bool]:
        used_indices: list[bool] = []

        used_indices.extend([True] * 2)
        used_indices.extend([False] * 2)
        used_indices.extend([True] * 2)

        return used_indices

    def jacobian_h(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        return transform_matrix_to_size(self.get_used_indices())

    def hx(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        return transform_vector_to_size(x, self.get_used_indices())

    def should_use_imu_rotation(self, context: ExtrapolationContext | None) -> bool:
        if context is None:
            return False

        if self.use_imu_rotation == TagUseImuRotation.ALWAYS:
            return True

        if self.use_imu_rotation == TagUseImuRotation.UNTIL_FIRST_NON_TAG_ROTATION:
            return context.has_gotten_rotation

        return False

    def prepare_input(
        self,
        data: AprilTagData,
        sensor_id: str,
        context: ExtrapolationContext | None = None,
    ) -> KalmanFilterInput | None:
        if data.WhichOneof("data") == "raw_tags":
            raise ValueError("Tags are not in processed format")

        input_list: list[list[float]] = []
        for tag in data.world_tags.tags:
            tag_id = tag.id
            if tag_id not in self.tags_in_world:
                continue

            T_camera_in_robot = create_transformation_matrix(
                rotation_matrix=get_np_from_matrix(
                    self.cameras_in_robot[sensor_id].rotation
                ),
                translation_vector=get_np_from_vector(
                    self.cameras_in_robot[sensor_id].position
                ),
            )
            T_tag_in_world = create_transformation_matrix(
                rotation_matrix=get_np_from_matrix(self.tags_in_world[tag_id].rotation),
                translation_vector=get_np_from_vector(
                    self.tags_in_world[tag_id].position
                ),
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

            R_robot_rotation_world: NDArray[np.float64] | None = None
            if self.should_use_imu_rotation(context):
                assert context is not None
                R_robot_rotation_world = make_transformation_matrix_p_d(
                    position=np.array([0, 0, 0]),
                    direction_vector=np.array([context.x[4], context.x[5], 0]),
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
            # rotation_angle_rad = np.atan2( <- correct rotation theta angle
            #    render_direction_vector[1] /*y*/, render_direction_vector[0] /*x*/
            # )

            datapoint = [
                render_pose[0],
                render_pose[1],
                render_direction_vector[0],
                render_direction_vector[1],
            ]

            input_list.append(datapoint)

        return KalmanFilterInput(
            input_list=self.get_avg_pose(input_list),
            sensor_id=sensor_id,
            sensor_type=KalmanFilterSensorType.APRIL_TAG,
            jacobian_h=self.jacobian_h,
            hx=self.hx,
        )
