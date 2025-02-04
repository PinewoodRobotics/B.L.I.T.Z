import asyncio
import time
import zlib
import cv2
from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.camera.transform import unfisheye_image
from project.common.image.query_helper.april_query_helper import AprilQueryHelper
from project.example.util.render.april_tag import render_april_tag
import pyvista as pv
import numpy as np

from project.example.util.render.render_2d import PygameWindow
from project.example.util.render.render_helper import AsyncPyVistaVisualizer
from generated.AprilTag_pb2 import AprilTags
from generated.Image_pb2 import ImageMessage


async def main():
    autobahn_server = Autobahn("localhost", 8080)
    await autobahn_server.begin()
    visualizer = PygameWindow()
    asyncio.create_task(visualizer.run())

    async def process_tags(msg: bytes):
        res = AprilTags()
        res.ParseFromString(msg)
        if res.tags:
            visualizer.update_objects(
                [
                    (tag.position_x_relative * 25, tag.position_z_relative * 25)
                    for tag in res.tags
                ]
            )

    async def process_camera(msg: bytes):
        image = ImageMessage()
        image.ParseFromString(msg)
        if image.camera_name == "custom1":
            image = cv2.imdecode(
                np.frombuffer(image.image, np.uint8), cv2.IMREAD_GRAYSCALE
            )
            cv2.imshow("image", image)
            cv2.waitKey(1)

    await autobahn_server.subscribe("apriltag/tag", process_tags)
    await autobahn_server.subscribe("apriltag/camera", process_camera)

    while True:
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())
