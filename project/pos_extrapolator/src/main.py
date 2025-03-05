import argparse
import asyncio
import time

import numpy as np

from generated.AprilTag_pb2 import AprilTags
from generated.Imu_pb2 import Imu
from generated.Odometry_pb2 import Odometry
from generated.RobotPosition_pb2 import RobotPosition
from generated.util.position_pb2 import Position2d
from generated.util.vector_pb2 import Vector2
from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address
from project.common.config import Config
from project.pos_extrapolator.src.kalman_filter import KalmanFilterStrategy
from project.pos_extrapolator.src.position_extrapolator import \
    PositionExtrapolator

parser = argparse.ArgumentParser()
parser.add_argument("--config", type=str, default=None)


async def main():
    args = parser.parse_args()
    config = Config.from_uncertainty_config(args.config)

    autobahn_server = Autobahn(Address("localhost", config.autobahn.port))
    await autobahn_server.begin()

    sensor_data_queue: asyncio.Queue[Odometry | AprilTags | Imu] = asyncio.Queue()

    async def process_tags(message: bytes):
        try:
            tags = AprilTags()
            tags.ParseFromString(message)
            await sensor_data_queue.put(tags)
        except Exception as e:
            print(f"Error parsing AprilTags message: {e}")

    async def process_odom(message: bytes):
        try:
            odom = Odometry()
            odom.ParseFromString(message)
            await sensor_data_queue.put(odom)
        except Exception as e:
            print(f"Error parsing Odometry message: {e}")

    async def process_imu(message: bytes):
        try:
            imu = Imu()
            imu.ParseFromString(message)
            await sensor_data_queue.put(imu)
        except Exception as e:
            print(f"Error parsing IMU message: {e}")

    await autobahn_server.subscribe(
        config.pos_extrapolator.message_config.post_tag_input_topic,
        process_tags,
    )

    await autobahn_server.subscribe(
        config.pos_extrapolator.message_config.post_odometry_input_topic,
        process_odom,
    )

    await autobahn_server.subscribe(
        config.pos_extrapolator.message_config.post_imu_input_topic,
        process_imu,
    )

    position_extrapolator = PositionExtrapolator(
        config.pos_extrapolator,
        KalmanFilterStrategy(config.pos_extrapolator.kalman_filter),
        config.pos_extrapolator.camera_configs,
        config.pos_extrapolator.tag_position_config,
        config.pos_extrapolator.imu_configs,
        config.pos_extrapolator.odom_configs,
    )

    while True:
        sensor_data = await sensor_data_queue.get()

        position_extrapolator.insert_data(sensor_data)
        filtered_position = position_extrapolator.get_position()

        await autobahn_server.publish(
            config.pos_extrapolator.message_config.post_robot_position_output_topic,
            RobotPosition(
                timestamp=time.time() * 1000,
                confidence=position_extrapolator.get_confidence(),
                estimated_position=Position2d(
                    position=Vector2(
                        x=filtered_position[0],
                        y=filtered_position[1],
                    ),
                    direction=Vector2(
                        x=np.cos(filtered_position[4]),
                        y=np.sin(filtered_position[4]),
                    ),
                ),
            ).SerializeToString(),
        )


if __name__ == "__main__":
    asyncio.run(main())
