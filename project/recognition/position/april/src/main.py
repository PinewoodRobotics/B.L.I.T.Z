import argparse
import asyncio
from multiprocessing import Queue
import random
import time
import signal

import cv2
import numpy as np
import pyapriltags

from generated.Image_pb2 import ImageMessage
from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address
from project.common.config import Config
from project.common.config_class.name import get_system_name
from project.recognition.position.april.src.camera import DetectionCamera

parser = argparse.ArgumentParser()
parser.add_argument("--config", type=str, default=None)


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


async def main():
    args = parser.parse_args()
    config = Config.from_uncertainty_config(args.config)

    autobahn_server = Autobahn(Address("localhost", config.autobahn.port))
    await autobahn_server.begin()

    camera_detector_list = []

    def signal_handler(signum, frame):
        nonlocal running
        print("\nReceived signal to terminate. Cleaning up...")
        running = False
        # Clean up cameras
        for camera in camera_detector_list:
            camera.release()
        # Clean up queues
        while not queue_tag.empty():
            queue_tag.get()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    queue_tag = Queue()

    for camera in config.cameras:
        if camera.pi_to_run_on != get_system_name():
            continue

        print(camera.name)

        camera_detector_list.append(
            DetectionCamera(
                config=camera,
                tag_size=config.april_detection.tag_size,
                detector_builder=lambda: build_detector(config),
                publication_lambda=lambda tags: queue_tag.put(tags),
                publication_image_lambda=lambda image: None,
            )
        )

    running = True
    while running:
        try:
            # Use timeout to allow checking running flag
            tags = await asyncio.to_thread(lambda: queue_tag.get(timeout=0.05))
            await autobahn_server.publish(
                config.april_detection.message.post_tag_output_topic,
                tags,
            )

            """
            try:
                queue_item = await asyncio.to_thread(lambda: queue_image.get(timeout=0.05))
                await publish_image(queue_item[0], queue_item[1])
            except Exception:
                pass
            """

        except Exception:
            if not running:
                break
            # Add small sleep to prevent CPU spinning
            await asyncio.sleep(0.01)
            continue

    print("Main loop ended, cleaning up...")
    # Final cleanup
    for camera in camera_detector_list:
        camera.release()


if __name__ == "__main__":
    asyncio.run(main())
