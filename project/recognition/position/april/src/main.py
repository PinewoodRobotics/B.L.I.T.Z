import asyncio
import random
import time
import numpy as np
import pyapriltags

from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.config import Config
from generated.AprilTag_pb2 import AprilTags
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
    config = Config.load_config()
    _detector = build_detector(config)
    autobahn_server = Autobahn("localhost", config.autobahn.port)
    await autobahn_server.begin()


if __name__ == "__main__":
    asyncio.run(main())


"""
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
"""

"""
            await autobahn_server.publish(
                config.april_detection.message.post_tag_output_topic,
                output.SerializeToString(),
            )
"""
