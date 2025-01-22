import asyncio
import time

from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.config import Config, Module
from project.common.config_class.filters.kalman_filter_config import MeasurementType
from project.common.config_class.pos_extrapolator import PositionExtrapolationMethod
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
    convert_tag_to_world_pos,
)
from project.recognition.position.pos_extrapolator.src.tag_pos_to_world import (
    TagPosToWorld,
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

    tag_pos_to_world = TagPosToWorld(
        config.pos_extrapolator.tag_position_config_file, mock=True
    )

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
        if isinstance(filter_strategy, KalmanFilterStrategy):
            current_time = time.time()

            filter_strategy.update_state_transition_matrix_5_5(
                current_time - last_timestamps[type(sensor_data)]
            )

            last_timestamps[type(sensor_data)] = current_time

            filter_strategy.predict()

        if isinstance(sensor_data, AprilTags):
            for tag in sensor_data.tags:
                start_time = time.time()
                pos = convert_tag_to_world_pos(
                    (
                        tag.position_x_relative,
                        tag.position_y_relative,
                        tag.position_z_relative,
                    ),
                    config,
                    tag_pos_to_world,
                    sensor_data.camera_name,
                )

                filter_strategy.filter_data(
                    [pos[0], pos[2], 0, 0, tag.angle_relative_to_camera_yaw],
                    MeasurementType.APRIL_TAG,
                )
                print(f"Time taken: {(time.time() - start_time) * 1000}ms")
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

        robot_pos = RobotPosition(
            camera_name=config.pos_extrapolator.cameras_to_analyze[0],
            timestamp=int(time.time()),
            confidence=filter_strategy.get_confidence(),
            estimated_position=(
                filtered_position[0],
                filtered_position[1],
                filtered_position[2],
            ),
            estimated_rotation=(filtered_position[3], filtered_position[4]),
        )

        await autobahn_server.publish(
            config.pos_extrapolator.message.post_robot_position_output_topic,
            robot_pos.SerializeToString(),
        )


if __name__ == "__main__":
    asyncio.run(main())
