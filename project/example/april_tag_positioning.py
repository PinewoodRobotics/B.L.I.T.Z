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

camera_matrix = [
    [
        1459.013092168164,
        0.0,
        941.1817368129706,
    ],
    [
        0.0,
        1450.9546373771313,
        523.0240888523196,
    ],
    [
        0.0,
        0.0,
        1.0,
    ],
]
dist_coeffs = [
    [
        -0.43237149459673446,
        0.19572749208462567,
        0.0006948679465891381,
        5.132481888695187e-5,
        -0.05070219401624212,
    ],
]


async def main():
    # Initialize Autobahn server
    autobahn_server = Autobahn("localhost", 8080)
    await autobahn_server.begin()

    # Initialize AprilTag detection helper
    april_tag_detection_helper = AprilQueryHelper(
        autobahn_server=autobahn_server,
        input_topic="apriltag/tag",
        output_topic="apriltag/camera",
    )
    await april_tag_detection_helper.begin_subscribe()
    visualizer = PygameWindow()

    # Create task for running the visualizer
    asyncio.create_task(visualizer.run())

    # Initialize camera
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # frame = unfisheye_image(frame, np.array(camera_matrix), np.array(dist_coeffs))

        res = await april_tag_detection_helper.send_and_wait_for_response(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), "left"
        )

        if res and res.tags:
            print(res.tags)
            visualizer.update_objects(
                [
                    (tag.position_x_relative * 100, tag.position_z_relative * 100)
                    for tag in res.tags
                ]
            )

        cv2.imshow("frame", frame)
        cv2.waitKey(1)


if __name__ == "__main__":
    asyncio.run(main())
