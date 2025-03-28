import argparse
import asyncio
import signal
import time

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
    camera_detector_list = []
    running = True
    last_stats = time.time()

    autobahn_server = Autobahn(Address("localhost", config.autobahn.port))
    await autobahn_server.begin()

    loop = asyncio.get_running_loop()

    def publish_nowait(topic: str, data: bytes):
        try:
            future = asyncio.run_coroutine_threadsafe(
                autobahn_server.publish(topic, data), loop
            )
            future.add_done_callback(lambda f: f.exception() if f.exception() else None)
        except Exception as e:
            print(f"Error in publish_nowait: {e}")

    for camera in config.cameras:
        if camera.pi_to_run_on != get_system_name():
            continue

        camera_detector_list.append(
            DetectionCamera(
                config=camera,
                tag_size=config.april_detection.tag_size,
                detector_builder=lambda: build_detector(config),
                publication_lambda=lambda tags: publish_nowait(
                    config.april_detection.message.post_tag_output_topic,
                    tags,
                ),
                publication_stats_lambda=lambda stats: (
                    publish_nowait(
                        config.april_detection.stats_topic,
                        stats,
                    )
                    if time.time() - last_stats > 1
                    else None
                ),
            )
        )

    while running:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
