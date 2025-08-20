import argparse
import asyncio
import random
import signal
import time

import cv2
import pyapriltags

from blitz.common.debug.logger import LogLevel, init_logging, success
from blitz.generated.thrift.config.apriltag.ttypes import AprilDetectionConfig
from blitz.generated.thrift.config.camera.ttypes import CameraParameters, CameraType
from autobahn_client.client import Autobahn
from autobahn_client.util import Address
from blitz.common.config import from_uncertainty_config
from blitz.common.util.math import get_np_from_matrix, get_np_from_vector
from blitz.common.util.system import get_system_name, load_basic_system_config
from blitz.recognition.position.april.src.camera.OV2311_camera import (
    AbstractCaptureDevice,
    OV2311Camera,
)
from blitz.recognition.position.april.src.detector import DetectionCamera

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


def get_camera_capture_device(camera: CameraParameters) -> AbstractCaptureDevice:
    if camera.camera_type == CameraType.OV2311.value:
        return OV2311Camera(
            camera.camera_path,
            camera.width,
            camera.height,
            camera.max_fps,
            get_np_from_matrix(camera.camera_matrix),
            get_np_from_vector(camera.dist_coeff),
        )

    raise ValueError(f"Unsupported camera type: {camera.camera_type}")


async def main():
    basic_system_config = load_basic_system_config()
    args = parser.parse_args()
    config = from_uncertainty_config(args.config)

    camera_detector_list = []

    autobahn_server = Autobahn(
        Address(
            basic_system_config.autobahn.host,
            basic_system_config.autobahn.port,
        )
    )
    await autobahn_server.begin()

    init_logging(
        "APRIL_SERVER",
        LogLevel(basic_system_config.logging.global_logging_level),
        system_pub_topic=basic_system_config.logging.global_log_pub_topic,
        autobahn=autobahn_server,
        system_name=get_system_name(),
    )

    loop = asyncio.get_running_loop()

    def publish_nowait(topic: str, data: bytes):
        asyncio.run_coroutine_threadsafe(autobahn_server.publish(topic, data), loop)

    success("Starting APRIL server")
    for camera in config.cameras:
        if camera is not None and camera.pi_to_run_on != get_system_name():
            continue

        success(f"Starting camera: {camera.name}")
        detector_cam = DetectionCamera(
            name=camera.name,
            video_capture=get_camera_capture_device(camera),
            tag_size=config.april_detection.tag_size,
            detector=build_detector(config.april_detection),
            publication_lambda=lambda tags: publish_nowait(
                config.april_detection.message.post_tag_output_topic,
                tags,
            ),
            publication_image_lambda=lambda message: publish_nowait(
                config.april_detection.message.post_camera_output_topic,
                message,
            ),
        )

        camera_detector_list.append(detector_cam)

        detector_cam.start()

    await asyncio.Event().wait()


def cli_main():
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
