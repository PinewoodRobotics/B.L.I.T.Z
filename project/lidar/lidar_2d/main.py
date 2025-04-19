import argparse
import asyncio
import math
import numpy as np
from rplidar import RPLidar
from generated.LidarMessage_pb2 import LidarMessage2d
from generated.lidar.lidar_pb2 import PointCloud2d, Scan2d
from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address
from project.common.config import Config
from project.common.util.name import get_system_name
from project.lidar.lidar_2d.lidar_bridge import LidarBridge

parser = argparse.ArgumentParser()
parser.add_argument("--config", type=str, default=None)


def from_polar(distance: float, angle: float) -> tuple[float, float]:
    return distance * math.cos(angle), distance * math.sin(angle)


async def main():
    args = parser.parse_args()
    config = Config.from_uncertainty_config(args.config)

    autobahn = Autobahn(
        Address(
            "localhost",
            config.autobahn.port,
        )
    )
    await autobahn.begin()

    pi_name = get_system_name()
    bridges: list[LidarBridge] = []
    for lidar_config in config.lidar_configs:
        if lidar_config.pi_to_run_on != pi_name:
            continue

        lidar = RPLidar(lidar_config.port)
        bridge = LidarBridge(lidar, lidar_config.name, lidar_config.transformation)
        bridges.append(bridge)

    async def publish_scan(scans: list[tuple[float, float, float]], lidar_name: str):
        pt_cloud = PointCloud2d()
        for scan in scans:
            distance_meters = scan[2] / 1000
            if (
                distance_meters > lidar_config.max_distance_meters
                or distance_meters < lidar_config.min_distance_meters
            ):
                continue

            x, y = from_polar(distance_meters, scan[1])
            array = bridge.to_robot_centered(np.array([x, y]))

            pt_cloud.ranges.append(
                Scan2d(position_x=float(array[0]), position_y=float(array[1]))
            )

        lidar_msg = LidarMessage2d(name=lidar_name, point_cloud=pt_cloud)

        await autobahn.publish(
            get_system_name() + "/lidar/scan", lidar_msg.SerializeToString()
        )

    while True:
        try:
            for bridge in bridges:
                await publish_scan(bridge.last_scan, bridge.name)
        except Exception as e:
            print(e)
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
