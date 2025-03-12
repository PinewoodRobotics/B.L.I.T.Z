import argparse
import asyncio

from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address
from project.common.config import Config
from project.common.config_class.name import get_system_name

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
        pass

    await autobahn.subscribe(
        get_system_name() + "/lidar/scan", process_incoming_point_cloud
    )

    while True:
        await asyncio.sleep(0.1)
