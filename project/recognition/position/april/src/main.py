import argparse
import asyncio
import signal
import time

import pyapriltags

from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address
from project.common.config import Config
from project.common.config_class.april_detection import AprilDetectionConfig
from project.common.util.system import get_system_name
from project.recognition.position.april.src.camera import DetectionCamera

parser = argparse.ArgumentParser()
parser.add_argument("--config", type=str, default=None)


def build_detector(config: AprilDetectionConfig):
    return pyapriltags.Detector(
        families=str(config.family),
        nthreads=config.nthreads,
        quad_decimate=config.quad_decimate,
        quad_sigma=config.quad_sigma,
        refine_edges=config.refine_edges,
        decode_sharpening=config.decode_sharpening,
        debug=0,
    )


async def main():
    args = parser.parse_args()
    config = Config.from_uncertainty_config(args.config)

    camera_detector_list = []

    autobahn_server = Autobahn(Address("localhost", config.autobahn.port))
    await autobahn_server.begin()

    loop = asyncio.get_running_loop()

    def publish_nowait(topic: str, data: bytes):
        asyncio.run_coroutine_threadsafe(autobahn_server.publish(topic, data), loop)

    for camera in config.cameras:
        if camera.pi_to_run_on != get_system_name():
            continue

        camera_detector_list.append(
            DetectionCamera(
                config=camera,
                tag_size=config.april_detection.tag_size,
                detector=build_detector(config.april_detection),
                publication_lambda=lambda tags: publish_nowait(
                    config.april_detection.message.post_tag_output_topic,
                    tags,
                ),
            )
        )

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
