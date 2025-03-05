import argparse
import asyncio
import random
import time

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

    detector = build_detector(config)
    autobahn_server = Autobahn(Address("localhost", config.autobahn.port))

    async def publish_image(image: np.ndarray, camera_name: str):
        nonlocal autobahn_server, config
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

    await autobahn_server.begin()
    camera_detector_list = []
    queue_tag = asyncio.Queue()
    queue_image = asyncio.Queue()

    async def process_queue():
        while True:
            try:
                tags = queue_tag.get_nowait()
                await autobahn_server.publish(
                    config.april_detection.message.post_tag_output_topic,
                    tags.SerializeToString(),
                )
            except asyncio.QueueEmpty:
                pass

            try:
                queue_item = queue_image.get_nowait()
                await publish_image(queue_item[0], queue_item[1])
            except asyncio.QueueEmpty:
                pass

    for camera in config.cameras:
        if camera.pi_to_run_on != get_system_name():
            continue

        camera_detector_list.append(
            DetectionCamera(
                config=camera,
                tag_size=config.april_detection.tag_size,
                detector=detector,
                publication_lambda=lambda tags: queue_tag.put_nowait(tags),
                publication_image_lambda=lambda image: queue_image.put_nowait(
                    (image, camera.name)
                ),
            )
        )

    await process_queue()


if __name__ == "__main__":
    asyncio.run(main())
