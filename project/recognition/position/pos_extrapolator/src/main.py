import asyncio
import time

import numpy as np
from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.config import Config, Module
from project.common.config_class.filters.kalman_filter_config import MeasurementType
from project.common.config_class.pos_extrapolator import (
    PosExtrapolatorConfig,
    PositionExtrapolationMethod,
)
from project.generated.project.common.proto.AprilTag_pb2 import AprilTags

from math_util import (
    get_rotation_matrix_deg,
    rotate_pitch_yaw,
    rotate_vector,
    translate_vector,
)
from project.generated.project.common.proto.RobotPosition_pb2 import RobotPosition
from project.recognition.position.pos_extrapolator.src.filter import FilterStrategy
from project.recognition.position.pos_extrapolator.src.filters.average import (
    AverageFilter,
)
from project.recognition.position.pos_extrapolator.src.filters.kalman import (
    KalmanFilterStrategy,
)
from project.recognition.position.pos_extrapolator.src.filters.weighted_average import (
    WeightedAverageFilter,
)
from project.recognition.position.pos_extrapolator.src.tag_pos_to_world import (
    TagPosToWorld,
)


async def main():
    processed_tag_positions: dict[str, list[RobotPosition]] = {}

    config = Config(
        "config.toml",
        exclude=[
            Module.IMAGE_RECOGNITION,
            Module.APRIL_DETECTION,
            Module.PROFILER,
        ],
    )

    autobahn_server = Autobahn("localhost", config.autobahn.port)
    await autobahn_server.begin()
    tag_pos_to_world = TagPosToWorld(config.pos_extrapolator.tag_position_config_file)
    filter_strategy: FilterStrategy
    match config.pos_extrapolator.position_extrapolation_method:
        case PositionExtrapolationMethod.AVERAGE_POSITION:
            filter_strategy = AverageFilter()
        case PositionExtrapolationMethod.WEIGHTED_AVERAGE_POSITION:
            filter_strategy = WeightedAverageFilter(config.weighted_avg_filter)
        case PositionExtrapolationMethod.KALMAN_LINEAR_FILTER:
            filter_strategy = KalmanFilterStrategy(config.kalman_filter)

    async def process_position(message: bytes):
        tags = AprilTags()
        tags.ParseFromString(message)
        camera_config = config.camera_parameters.camera_parameters[tags.camera_name]
        rotation_matrix = get_rotation_matrix_deg(
            camera_config.rotation_vector[0], camera_config.rotation_vector[1]
        )
        translation_vector = np.array(camera_config.translation_vector)

        for tag in tags.tags:
            tag_vector = np.array(
                [
                    tag.position_x_relative,
                    tag.position_y_relative,
                    tag.position_z_relative,
                ]
            )
            rotated_tag_vector = rotate_vector(tag_vector, rotation_matrix)
            translated_tag_vector = translate_vector(
                rotated_tag_vector, translation_vector
            )

            tag.angle_relative_to_camera_pitch, tag.angle_relative_to_camera_yaw = (
                rotate_pitch_yaw(
                    tag.angle_relative_to_camera_pitch,
                    tag.angle_relative_to_camera_yaw,
                    camera_config.rotation_vector[0],
                    camera_config.rotation_vector[1],
                )
            )

            world_pos = tag_pos_to_world.get_world_pos(
                (
                    translated_tag_vector[0],
                    translated_tag_vector[1],
                    translated_tag_vector[2],
                )
            )

            processed_tag_positions[tags.camera_name].append(
                RobotPosition(
                    camera_name=tags.camera_name,
                    timestamp=int(time.time()),
                    confidence=0.0,
                    estimated_position=world_pos,
                    estimated_rotation=[
                        tag.angle_relative_to_camera_pitch,
                        tag.angle_relative_to_camera_yaw,
                    ],
                )
            )

    await autobahn_server.subscribe(
        config.pos_extrapolator.message.post_tag_input_topic,
        process_position,
    )

    while True:
        if config.pos_extrapolator.cameras_to_analyze in processed_tag_positions:
            if isinstance(filter_strategy, KalmanFilterStrategy):
                filter_strategy.predict()

            for tag in processed_tag_positions[
                config.pos_extrapolator.cameras_to_analyze
            ]:
                filter_strategy.filter_data(
                    [
                        tag.estimated_position[0],
                        tag.estimated_position[1],
                        tag.estimated_position[2],
                        0,
                        0,
                        tag.estimated_rotation[0],
                        tag.estimated_rotation[1],
                    ],
                    MeasurementType.APRIL_TAG,
                )

            filtered_position = filter_strategy.get_filtered_data()

            robot_pos = RobotPosition(
                camera_name=config.pos_extrapolator.cameras_to_analyze,
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

        await asyncio.sleep(1)
