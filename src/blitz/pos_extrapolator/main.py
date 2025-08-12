# TODO: need to add a better way to handle the non-used indices in sensors (config method).

import argparse
import asyncio
import time

from autobahn_client import Address, Autobahn
import numpy as np

from blitz.common.config import from_uncertainty_config
from blitz.common.util.extension import subscribe_to_multiple_topics
from blitz.common.util.parser import get_default_process_parser
from blitz.common.util.system import load_basic_system_config
from blitz.generated.proto.python.sensor.apriltags_pb2 import AprilTagData
from blitz.generated.proto.python.sensor.general_sensor_data_pb2 import (
    GeneralSensorData,
)
from blitz.generated.proto.python.sensor.imu_pb2 import ImuData
from blitz.generated.proto.python.sensor.odometry_pb2 import OdometryData
from blitz.generated.proto.python.util.position_pb2 import RobotPosition
from blitz.generated.thrift.config.ttypes import Config
from blitz.pos_extrapolator.data_prep import DataPreparerManager
from blitz.pos_extrapolator.filters.extended_kalman_filter import (
    ExtendedKalmanFilterStrategy,
)
from blitz.pos_extrapolator.filters.kalman_filter import KalmanFilterStrategy
from blitz.pos_extrapolator.position_extrapolator import PositionExtrapolator
from blitz.pos_extrapolator.preparers.AprilTagPreparer import (
    AprilTagConfig,
    AprilTagDataPreparerConfig,
)
from blitz.pos_extrapolator.preparers.ImuDataPreparer import ImuDataPreparerConfig
from blitz.pos_extrapolator.preparers.OdomDataPreparer import OdomDataPreparerConfig


async def main():
    system_config = load_basic_system_config()
    config = from_uncertainty_config(get_default_process_parser().parse_args().config)

    autobahn_server = Autobahn(
        Address(system_config.autobahn.host, system_config.autobahn.port)
    )
    await autobahn_server.begin()

    if config.pos_extrapolator.enable_imu:
        DataPreparerManager.set_config(
            ImuData, ImuDataPreparerConfig(config.pos_extrapolator.imu_config)
        )
    if config.pos_extrapolator.enable_odom:
        DataPreparerManager.set_config(
            OdometryData, OdomDataPreparerConfig(config.pos_extrapolator.odom_config)
        )

    if config.pos_extrapolator.enable_tags:
        DataPreparerManager.set_config(
            AprilTagData,
            AprilTagDataPreparerConfig(
                config=AprilTagConfig(
                    tags_in_world=config.pos_extrapolator.tag_position_config,
                    cameras_in_robot=config.pos_extrapolator.camera_position_config,
                    use_imu_rotation=config.pos_extrapolator.tag_use_imu_rotation,
                ),
            ),
        )

    position_extrapolator = PositionExtrapolator(
        config.pos_extrapolator,
        ExtendedKalmanFilterStrategy(config.pos_extrapolator.kalman_filter_config),
        DataPreparerManager(),
    )

    async def process_data(message: bytes):
        data = GeneralSensorData.FromString(message)
        one_of_name = data.WhichOneof("data")
        position_extrapolator.insert_sensor_data(
            data.__getattribute__(one_of_name), data.sensor_id
        )

    subscribe_topics = [
        config.pos_extrapolator.message_config.post_tag_input_topic,
        config.pos_extrapolator.message_config.post_odometry_input_topic,
        config.pos_extrapolator.message_config.post_imu_input_topic,
    ]

    if (
        hasattr(config.pos_extrapolator, "composite_publish_topic")
        and config.pos_extrapolator.composite_publish_topic is not None
    ):
        subscribe_topics.append(config.pos_extrapolator.composite_publish_topic)

    await subscribe_to_multiple_topics(
        autobahn_server,
        subscribe_topics,
        process_data,
    )

    while True:
        filtered_position = position_extrapolator.get_robot_position_estimate()

        proto_position = RobotPosition()
        proto_position.timestamp = time.time() * 1000
        proto_position.confidence = position_extrapolator.get_confidence()
        proto_position.position_2d.position.x = filtered_position[0]
        proto_position.position_2d.position.y = filtered_position[1]
        proto_position.position_2d.direction.x = filtered_position[4]
        proto_position.position_2d.direction.y = filtered_position[5]
        # proto_position.P.extend(position_extrapolator.get_position_covariance())

        await autobahn_server.publish(
            config.pos_extrapolator.message_config.post_robot_position_output_topic,
            proto_position.SerializeToString(),
        )

        await asyncio.sleep(
            config.pos_extrapolator.time_s_between_position_sends
            if config.pos_extrapolator.time_s_between_position_sends
            else 0.025
        )


if __name__ == "__main__":
    asyncio.run(main())
