import asyncio
import time
import cv2
import numpy as np

from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.config import Config, Module
from project.common.config_class.filters.kalman_filter_config import MeasurementType
from project.common.config_class.pos_extrapolator import PositionExtrapolationMethod
from project.common.util.math import (
    create_transformation_matrix,
    from_float_list,
    get_translation_rotation_components,
    get_world_pos,
)
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
from project.generated.project.common.proto.RobotPosition_pb2 import RobotPosition
from project.recognition.position.pos_extrapolator.src.world_conversion import (
    WorldConversion,
)


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

    autobahn_server = Autobahn("localhost", config.autobahn.port)
    await autobahn_server.begin()

    sensor_data_queue: asyncio.Queue[Odometry | AprilTags | Imu] = asyncio.Queue()

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

    world_conversion = WorldConversion(
        filter_strategy,
        config.pos_extrapolator.tag_configs.config,
        config.pos_extrapolator.imu_configs,
    )

    while True:
        sensor_data = await sensor_data_queue.get()
        world_conversion.insert_data(sensor_data)

        filtered_position = world_conversion.get_position()

        await autobahn_server.publish(
            config.pos_extrapolator.message.post_robot_position_output_topic,
            RobotPosition(
                camera_name=config.pos_extrapolator.cameras_to_analyze[0],
                timestamp=time.time() * 1000,
                confidence=world_conversion.get_confidence(),
                estimated_position=(
                    filtered_position[0],
                    filtered_position[1],
                    filtered_position[2],
                ),
                estimated_rotation=[filtered_position[4]],
            ).SerializeToString(),
        )


if __name__ == "__main__":
    asyncio.run(main())
