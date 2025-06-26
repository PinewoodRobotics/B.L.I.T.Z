import argparse
import asyncio
import time

from autobahn_client import Address, Autobahn
import numpy as np

from blitz.common.config import from_uncertainty_config
from blitz.common.util.extension import subscribe_to_multiple_topics
from blitz.common.util.parser import get_default_process_parser
from blitz.generated.proto.python.sensor.apriltags_pb2 import AprilTagData
from blitz.generated.proto.python.sensor.general_sensor_data_pb2 import (
    GeneralSensorData,
)
from blitz.generated.proto.python.sensor.imu_pb2 import ImuData
from blitz.generated.proto.python.sensor.odometry_pb2 import OdometryData
from blitz.generated.proto.python.util.position_pb2 import RobotPosition
from blitz.pos_extrapolator.data_prep import DataPreparerManager
from blitz.pos_extrapolator.kalman_filter import KalmanFilterStrategy
from blitz.pos_extrapolator.position_extrapolator import PositionExtrapolator
from blitz.pos_extrapolator.preparers.AprilTagPreparer import AprilTagDataPreparerConfig
from blitz.pos_extrapolator.preparers.ImuDataPreparer import ImuDataPreparerConfig
from blitz.pos_extrapolator.preparers.OdomDataPreparer import OdomDataPreparerConfig


async def main():
    config = from_uncertainty_config(get_default_process_parser().parse_args().config)

    autobahn_server = Autobahn(Address(config.autobahn.host, config.autobahn.port))
    await autobahn_server.begin()

    DataPreparerManager.set_config(
        ImuData, ImuDataPreparerConfig(config.pos_extrapolator.imu_config)
    )
    DataPreparerManager.set_config(
        OdometryData, OdomDataPreparerConfig(config.pos_extrapolator.odom_config)
    )
    DataPreparerManager.set_config(
        AprilTagData,
        AprilTagDataPreparerConfig(
            (
                config.pos_extrapolator.tag_position_config,
                config.pos_extrapolator.camera_position_config,
            ),
        ),
    )

    position_extrapolator = PositionExtrapolator(
        config.pos_extrapolator,
        KalmanFilterStrategy(config.pos_extrapolator.kalman_filter_config),
        DataPreparerManager(),
    )

    async def process_data(message: bytes):
        data = GeneralSensorData.FromString(message)
        one_of_name = data.WhichOneof("data")
        position_extrapolator.insert_sensor_data(
            data.__getattribute__(one_of_name), data.sensor_id
        )

    await subscribe_to_multiple_topics(
        autobahn_server,
        [
            config.pos_extrapolator.message_config.post_tag_input_topic,
            config.pos_extrapolator.message_config.post_odometry_input_topic,
            config.pos_extrapolator.message_config.post_imu_input_topic,
        ],
        process_data,
    )

    while True:
        filtered_position = position_extrapolator.get_robot_position_estimate()

        proto_position = RobotPosition()
        proto_position.timestamp = time.time() * 1000
        proto_position.confidence = position_extrapolator.get_confidence()
        proto_position.position_2d.position.x = filtered_position[0]
        proto_position.position_2d.position.y = filtered_position[1]
        proto_position.position_2d.direction.x = np.cos(filtered_position[4])
        proto_position.position_2d.direction.y = np.sin(filtered_position[4])

        await autobahn_server.publish(
            config.pos_extrapolator.message_config.post_robot_position_output_topic,
            proto_position.SerializeToString(),
        )

        await asyncio.sleep(
            0.05
        )  # TODO: figure out the delay that needs to be set here.


if __name__ == "__main__":
    asyncio.run(main())
