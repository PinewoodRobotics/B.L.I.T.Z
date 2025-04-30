from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from render.cube_point_cloud import CubePointCloud
from render.user import FlyController
from render.axes import Axes
from render.ground import GroundGrid
from render.objects.apriltag import AprilTag
import random
import math
import sys
import asyncio
import threading
from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address
from object_pipelines.pipeline_manager import PipelineManager
from render.world import World


app = Ursina()
world = World()


async def main():
    autobahn_server = Autobahn(Address("localhost", 8080))
    await autobahn_server.begin()

    pipeline_manager = PipelineManager()

    for topic in pipeline_manager.get_all_topics():
        pipeline_class = pipeline_manager.get_pipeline(topic)
        if pipeline_class:
            pipeline = pipeline_class()

            async def create_callback(pipeline_instance):
                async def callback(message: bytes):
                    global world
                    await pipeline_instance.process(world, message)

                return callback

            await autobahn_server.subscribe(topic, await create_callback(pipeline))
    while True:
        await asyncio.sleep(1)


def run_main():
    asyncio.run(main())


thread = threading.Thread(target=run_main)
thread.daemon = True
thread.start()

app.run()
