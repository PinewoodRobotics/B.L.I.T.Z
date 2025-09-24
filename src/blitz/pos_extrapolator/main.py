# TODO: need to add a better way to handle the non-used indices in sensors (config method).

import argparse
import asyncio
import time

from autobahn_client import Address, Autobahn
import numpy as np

from blitz.common.config import from_uncertainty_config
from blitz.common.debug.logger import LogLevel, init_logging
from blitz.common.debug.pubsub_replay import ReplayAutobahn, autolog
from blitz.common.debug.replay_recorder import init_replay_recorder
from blitz.common.util.extension import subscribe_to_multiple_topics
from blitz.common.util.parser import get_default_process_parser
from blitz.common.util.system import (
    BasicSystemConfig,
    SystemStatus,
    get_system_status,
    load_basic_system_config,
)
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


def init_utilities(config: Config):
    init_logging("POSE_EXTRAPOLATOR", LogLevel.DEBUG)

    if get_system_status() == SystemStatus.SIMULATION:
        init_replay_recorder(replay_path="latest", mode="r")
    elif config.record_replay:
        init_replay_recorder(folder_path=config.replay_folder_path)


def get_autobahn_server(config: Config, system_config: BasicSystemConfig):
    address = Address(system_config.autobahn.host, system_config.autobahn.port)
    autobahn_server = Autobahn(address)

    if get_system_status() == SystemStatus.SIMULATION:
        autobahn_server = ReplayAutobahn(
            replay_path="latest",
            publish_on_real_autobahn=True,
            address=address,
        )

    return autobahn_server


def init_data_preparer_manager(config: Config):
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


def get_subscribe_topics(config: Config):
    subscribe_topics: list[str] = []
    if config.pos_extrapolator.enable_imu:
        subscribe_topics.append(config.pos_extrapolator.message_config.post_imu_input_topic)
    if config.pos_extrapolator.enable_odom:
        subscribe_topics.append(config.pos_extrapolator.message_config.post_odometry_input_topic)
    if config.pos_extrapolator.enable_tags:
        subscribe_topics.append(config.pos_extrapolator.message_config.post_tag_input_topic)

    return subscribe_topics


async def main():
    system_config = load_basic_system_config()
    config = from_uncertainty_config(get_default_process_parser().parse_args().config)

    init_utilities(config)
    autobahn_server = get_autobahn_server(config, system_config)
    await autobahn_server.begin()

    init_data_preparer_manager(config)

    subscribe_topics = get_subscribe_topics(config)

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
        proto_position = position_extrapolator.get_robot_position()

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
