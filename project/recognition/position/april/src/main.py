import asyncio
import random
import time
import cv2
import numpy as np
import pyapriltags

from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.config import Config, Module
from generated.AprilTag_pb2 import AprilTags
from generated.Image_pb2 import ImageMessage
from project.recognition.position.april.src.camera import Camera
from util import from_detection_to_proto


def build_detector(config: Config):
    return pyapriltags.Detector(
        families=str(config.april_detection.family),
        nthreads=config.april_detection.nthreads,
        quad_decimate=config.april_detection.quad_decimate,
        quad_sigma=config.april_detection.quad_sigma,
        refine_edges=config.april_detection.refine_edges,
        decode_sharpening=config.april_detection.decode_sharpening,
        debug=0,
    )


async def process_image(
    image: np.ndarray,
    camera_matrix: np.ndarray,
    detector: pyapriltags.Detector,
    tag_size: float,
    camera_name: str,
):
    fx, fy, cx, cy = (
        camera_matrix[0, 0],
        camera_matrix[1, 1],
        camera_matrix[0, 2],
        camera_matrix[1, 2],
    )
    output = AprilTags(
        camera_name=camera_name,
        image_id=random.randint(0, 1000000),
        tags=[
            from_detection_to_proto(tag)
            for tag in detector.detect(
                image,
                estimate_tag_pose=True,
                camera_params=((fx, fy, cx, cy)),
                tag_size=tag_size,
            )
        ],
        timestamp=int(time.time() * 1000),
    )

    return output


async def main():
    config = Config(
        "config.toml",
        exclude=[
            Module.IMAGE_RECOGNITION,
            Module.PROFILER,
            Module.KALMAN_FILTER,
            Module.POS_EXTRAPOLATOR,
            Module.WEIGHTED_AVG_FILTER,
            Module.KALMAN_FILTER,
        ],
    )

    detector = build_detector(config)
    autobahn_server = Autobahn("localhost", config.autobahn.port)
    await autobahn_server.begin()

    cameras = [
        (
            camera_name,
            Camera(config.camera_parameters.camera_parameters[camera_name]),
        )
        for camera_name in config.april_detection.cameras
    ]

    camera = cameras[0]
    camera_name = camera[0]

    number_sent = 0
    while True:
        _process_start_time = time.time()
        got, image, mtrx = camera[1].read_with_cropping(
            np.array([0, 0, 0]), np.array([100, 100, 100])
        )
        # print((time.time() - process_start_time) * 1000)
        # image = cv2.bitwise_not(image)
        # print(f"Took {(time.time() - time_start) * 1000}")

        if not got or image is None or mtrx is None:
            if image is None:
                camera[1].release()
                cameras[0] = (
                    camera_name,
                    Camera(config.camera_parameters.camera_parameters[camera_name]),
                )
            continue

        if number_sent > 5:
            await autobahn_server.publish(
                config.april_detection.message.post_camera_output_topic,
                ImageMessage(
                    image_id=random.randint(0, 1000000),
                    image=cv2.imencode(".jpg", image)[1].tobytes(),
                    camera_name=camera_name,
                    timestamp=int(time.time() * 1000),
                    height=image.shape[0],
                    width=image.shape[1],
                    is_gray=False,
                ).SerializeToString(),
            )
            number_sent = 0
        number_sent += 1

        output = await process_image(
            image,
            mtrx,
            detector,
            config.april_detection.tag_size,
            camera_name,
        )

        if len(output.tags) > 0:
            print("Found!")
            await autobahn_server.publish(
                config.april_detection.message.post_tag_output_topic,
                output.SerializeToString(),
            )


if __name__ == "__main__":
    asyncio.run(main())
