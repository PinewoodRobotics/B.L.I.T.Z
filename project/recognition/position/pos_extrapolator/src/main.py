import asyncio
import time
import cv2
import numpy as np

from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.config import Config, Module
from project.common.config_class.filters.kalman_filter_config import MeasurementType
from project.common.config_class.pos_extrapolator import PositionExtrapolationMethod
from project.common.util.math import create_transformation_matrix, get_world_pos
from project.generated.project.common.proto.AprilTag_pb2 import AprilTags
from project.generated.project.common.proto.Imu_pb2 import Imu
from project.generated.project.common.proto.Odometry_pb2 import Odometry
from project.recognition.position.pos_extrapolator.src.filter import FilterStrategy
from project.recognition.position.pos_extrapolator.src.filters.average import (
    AverageFilter,
)
from project.recognition.position.pos_extrapolator.src.filters.weighted_average import (
    WeightedAverageFilter,
)
from project.recognition.position.pos_extrapolator.src.filters.kalman import (
    KalmanFilterStrategy,
)
from project.recognition.position.pos_extrapolator.src.math_util import (
    from_float_list,
    make_rotation_matrix,
)
from project.generated.project.common.proto.RobotPosition_pb2 import RobotPosition


async def main():
    config = Config(
        "config.toml",
        exclude=[
            Module.IMAGE_RECOGNITION,
            Module.APRIL_DETECTION,
            Module.PROFILER,
            Module.WEIGHTED_AVG_FILTER,
        ],
    )

    last_timestamps: dict[type[Odometry | AprilTags | Imu], float] = {
        Odometry: 0,
        AprilTags: 0,
        Imu: 0,
    }

    autobahn_server = Autobahn("localhost", config.autobahn.port)
    await autobahn_server.begin()

    sensor_data_queue: asyncio.Queue[Odometry | AprilTags | Imu] = asyncio.Queue()

    # tag_pos_to_world = TagPosToWorld(config.pos_extrapolator.tag_configs, mock=True)

    # Initialize filter strategy based on config
    filter_strategy: FilterStrategy
    match config.pos_extrapolator.position_extrapolation_method:
        case PositionExtrapolationMethod.AVERAGE_POSITION.value:
            filter_strategy = AverageFilter()
        case PositionExtrapolationMethod.WEIGHTED_AVERAGE_POSITION.value:
            filter_strategy = WeightedAverageFilter(config.weighted_avg_filter)
        case PositionExtrapolationMethod.KALMAN_LINEAR_FILTER.value:
            filter_strategy = KalmanFilterStrategy(config.kalman_filter)

    async def process_tags(message: bytes):
        tags = AprilTags()
        tags.ParseFromString(message)
        await sensor_data_queue.put(tags)

    async def process_odom(message: bytes):
        odom = Odometry()
        odom.ParseFromString(message)
        await sensor_data_queue.put(odom)

    async def process_imu(message: bytes):
        imu = Imu()
        imu.ParseFromString(message)
        await sensor_data_queue.put(imu)

    await autobahn_server.subscribe(
        config.pos_extrapolator.message.post_tag_input_topic,
        process_tags,
    )

    await autobahn_server.subscribe(
        config.pos_extrapolator.message.post_odometry_input_topic,
        process_odom,
    )

    await autobahn_server.subscribe(
        config.pos_extrapolator.message.post_imu_input_topic,
        process_imu,
    )

    while True:
        start_time = time.time()
        sensor_data = await sensor_data_queue.get()
        pos = []
        if isinstance(filter_strategy, KalmanFilterStrategy):
            current_time = time.time()

            filter_strategy.update_state_transition_matrix_5_5(
                current_time - last_timestamps[type(sensor_data)]
            )

            last_timestamps[type(sensor_data)] = current_time

            filter_strategy.predict()

        if isinstance(sensor_data, AprilTags):
            for tag in sensor_data.tags:
                # Convert tag position and angles to numpy arrays

                # Get tag's global config
                tag_config = config.pos_extrapolator.tag_configs.config[str(tag.tag_id)]

                C_t = from_float_list(list(tag.pose_R), 3, 3)
                tag_pos = np.array(
                    [
                        tag.pose_t[0],
                        tag.pose_t[1],
                        tag.pose_t[2],
                    ]
                )

                print(C_t)

                T_in_camera = create_transformation_matrix(C_t, tag_pos)

                world_transform = get_world_pos(T_in_camera, tag_config.transformation)

                # Extract translation and rotation components from the transformation matrix
                translation_component = world_transform[:3, 3]  # Last column (x, y, z)
                rotation_component = world_transform[:3, :3]  # 3x3 rotation matrix

                pos = [tag_pos[0], tag_pos[2]]

                # print(translation_component, rotation_component)

                filter_strategy.filter_data(
                    [
                        translation_component[0],
                        translation_component[2],
                        0,
                        0,
                        tag.angle_relative_to_camera_yaw,
                    ],
                    MeasurementType.APRIL_TAG,
                )
        elif isinstance(sensor_data, Odometry):
            filter_strategy.filter_data(
                [
                    sensor_data.x,
                    sensor_data.y,
                    sensor_data.vx,
                    sensor_data.vy,
                    sensor_data.theta,
                ],
                MeasurementType.ODOMETRY,
            )
        elif isinstance(sensor_data, Imu):
            filter_strategy.filter_data(
                [
                    sensor_data.x,
                    sensor_data.y,
                    sensor_data.acceleration_x,
                    sensor_data.acceleration_y,
                    sensor_data.yaw,
                ],
                MeasurementType.IMU,
            )

        filtered_position = filter_strategy.get_filtered_data()

        if len(pos) != 0:
            robot_pos = RobotPosition(
                camera_name=config.pos_extrapolator.cameras_to_analyze[0],
                timestamp=time.time() * 1000,
                confidence=filter_strategy.get_confidence(),
                estimated_position=(
                    filtered_position[0],
                    filtered_position[1],
                    filtered_position[2],
                ),
                estimated_rotation=(pos[0], pos[1]),
            )

        await autobahn_server.publish(
            config.pos_extrapolator.message.post_robot_position_output_topic,
            robot_pos.SerializeToString(),
        )


if __name__ == "__main__":
    asyncio.run(main())
