import asyncio
import time

from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.config import Config, Module
from project.common.config_class.pos_extrapolator import PositionExtrapolationMethod
from project.generated.project.common.proto.AprilTag_pb2 import AprilTags
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
from project.recognition.position.pos_extrapolator.src.tag_pos_to_world import (
    TagPosToWorld,
)
from project.recognition.position.pos_extrapolator.src.sensors.april_tag import (
    AprilTagSensorProcessor,
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

    autobahn_server = Autobahn("localhost", config.autobahn.port)
    await autobahn_server.begin()

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

    # Initialize AprilTagSensorProcessor
    april_tag_processor = AprilTagSensorProcessor(
        cameras_to_analyze=config.pos_extrapolator.cameras_to_analyze,
        config=config,
        tag_pos_to_world=tag_pos_to_world,
        filter_strategy=filter_strategy,
        only_tags=True,
        get_estimated_position=(
            filter_strategy.get_filtered_data if filter_strategy else None
        ),
    )

    async def process_tags(message: bytes):
        tags = AprilTags()
        tags.ParseFromString(message)

        # Clear previous positions for this camera before processing new ones
        april_tag_processor.current_positions[tags.camera_name] = []

        april_tag_processor.on_message(tags)

        if april_tag_processor.is_all_cameras_available():
            if isinstance(filter_strategy, KalmanFilterStrategy):
                filter_strategy.predict()

            april_tag_processor.dump_data()
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

    await autobahn_server.subscribe(
        config.pos_extrapolator.message.post_tag_input_topic,
        process_tags,
    )

    while True:
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())
