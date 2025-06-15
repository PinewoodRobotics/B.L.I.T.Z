import argparse
import asyncio

from blitz.generated.lidar.lidar_pb2 import PointCloud2d
from blitz.common.autobahn_python.autobahn import Autobahn
from blitz.common.autobahn_python.util import Address
from blitz.common.config import Config

parser = argparse.ArgumentParser()
parser.add_argument("--config", type=str, default=None)


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

    async def process_incoming_point_cloud(point_cloud: bytes):
        point_cloud_decoded = PointCloud2d.FromString(point_cloud)

    await autobahn.subscribe("lidar/scan2d", process_incoming_point_cloud)

    while True:
        await asyncio.sleep(0.1)
