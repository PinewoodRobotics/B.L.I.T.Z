import asyncio
import random
import threading
import time
import cv2
import nats
import numpy as np
import pyapriltags
from nats.aio.msg import Msg
from pyinstrument import Profiler

from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.config import Config, Module
from project.common.config_class.camera_parameters import CameraParameters
from project.generated.project.common.proto.AprilTag_pb2 import AprilTags, Tag
from project.generated.project.common.proto.Image_pb2 import ImageMessage
import msgpack_numpy as m
from project.common.image.image_util import from_proto_to_cv2
from project.recognition.position.april.src.camera import Camera
from util import from_detection_to_proto


def get_detector(config: Config):
    return pyapriltags.Detector(
        families=str(config.april_detection.family),
        nthreads=config.april_detection.nthreads,
        quad_decimate=config.april_detection.quad_decimate,
        quad_sigma=config.april_detection.quad_sigma,
        refine_edges=config.april_detection.refine_edges,
        decode_sharpening=config.april_detection.decode_sharpening,
        debug=0,
    )


def input_thread(config: Config):
    global user_input
    while True:
        user_input = input()
        if user_input == "reload":
            config.reload()


async def process_image(
    image: np.ndarray,
    config: CameraParameters,
    detector: pyapriltags.Detector,
    tag_size: float,
    camera_name: str,
):
    tags = detector.detect(
        image,
        estimate_tag_pose=True,
        camera_params=(
            config.get_fxy()[0],
            config.get_fxy()[1],
            config.get_center()[0],
            config.get_center()[1],
        ),
        tag_size=tag_size,
    )

    image_id = random.randint(0, 1000000)
    timestamp = int(time.time() * 1000)

    output = AprilTags(
        camera_name=camera_name,
        image_id=image_id,
        tags=[from_detection_to_proto(tag) for tag in tags],
        timestamp=timestamp,
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
    thread = threading.Thread(target=input_thread, daemon=True, args=(config,))
    thread.start()
    detector = get_detector(config)
    autobahn_server = Autobahn("localhost", config.autobahn.port)
    await autobahn_server.begin()

    cameras = [
        (
            camera_name,
            Camera(config.camera_parameters.camera_parameters[camera_name]),
        )
        for camera_name in config.april_detection.cameras
    ]

    # Initialize FPS tracking dictionaries for each camera
    fps_stats = {
        camera[0]: {"start_time": time.time(), "counter": 0, "fps": 0}
        for camera in cameras
    }

    while True:
        for camera in cameras:
            camera_name = camera[0]
            process_start_time = time.time()

            got, image = camera[1].read()
            if not got:
                print(f"Failed to read image from camera {camera_name}")
                continue

            _, compressed_image = cv2.imencode(".jpg", image)
            image_id = random.randint(0, 1000000)
            timestamp = int(time.time() * 1000)
            """
            await autobahn_server.publish(
                config.april_detection.message.post_camera_output_topic,
                ImageMessage(
                    image_id=image_id,
                    image=compressed_image.tobytes(),
                    camera_name=camera_name,
                    timestamp=timestamp,
                    height=image.shape[0],
                    width=image.shape[1],
                    is_gray=False,
                ).SerializeToString(),
            )
            """

            output = await process_image(
                cv2.cvtColor(image, cv2.COLOR_BGR2GRAY),
                camera[1].config,
                detector,
                config.april_detection.tag_size,
                camera_name,
            )

            if len(output.tags) > 0:
                print(output)
                await autobahn_server.publish(
                    config.april_detection.message.post_tag_output_topic,
                    output.SerializeToString(),
                )

            # Update FPS calculation including processing time
            process_end_time = time.time()
            fps_stats[camera_name]["counter"] += 1

            if (
                process_end_time - fps_stats[camera_name]["start_time"] > 1
            ):  # Update FPS every second
                elapsed_time = process_end_time - fps_stats[camera_name]["start_time"]
                fps = fps_stats[camera_name]["counter"] / elapsed_time
                process_time = (
                    process_end_time - process_start_time
                ) * 1000  # Convert to milliseconds
                print(
                    f"Camera {camera_name}: {fps:.1f} FPS, {process_time:.1f}ms per frame"
                )
                fps_stats[camera_name]["counter"] = 0
                fps_stats[camera_name]["start_time"] = process_end_time


if __name__ == "__main__":
    asyncio.run(main())
