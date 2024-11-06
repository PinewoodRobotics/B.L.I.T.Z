import asyncio
import cv2
import nats
from nats.aio.msg import Msg
from nats.aio.client import Client
import numpy as np
from common import logger
from common.config import Config, Module
from common.msg.image import TransformImageMessage


async def handle_message(nc: Client, msg: Msg, config: Config):
    loaded_class = TransformImageMessage.from_bytes(msg.data)

    if loaded_class.camera_name not in config.camera_feed_cleaner.cameras:
        return

    camera_matrix = np.array(
        config.camera_feed_cleaner.cameras[loaded_class.camera_name].camera_matrix
    )
    dist_coeff = np.array(
        config.camera_feed_cleaner.cameras[loaded_class.camera_name].dist_coeff
    )
    image = loaded_class.from_image_to_cv2()
    height, width = image.shape[:2]

    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
        camera_matrix,
        dist_coeff,
        (width, height),
        1,
        (width, height),
    )
    map1, map2 = cv2.initUndistortRectifyMap(
        camera_matrix,
        dist_coeff,
        np.eye(3),
        new_camera_matrix,
        (width, height),
        cv2.CV_16SC2,
    )

    frame = cv2.remap(
        image,
        map1,
        map2,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
    )

    if loaded_class.do_crop:
        side_crop_percent = 0.2
        top_bottom_crop_percent = 0.2

        side_crop = int(width * side_crop_percent)
        top_bottom_crop = int(height * top_bottom_crop_percent)

        x_start = side_crop
        x_end = width - side_crop
        y_start = top_bottom_crop
        y_end = height - top_bottom_crop

        frame = frame[y_start:y_end, x_start:x_end]

    loaded_class.from_cv2(frame, loaded_class.camera_name)
    await nc.publish(
        config.camera_feed_cleaner.image_output_topic,
        loaded_class.to_json().encode("utf-8"),
    )


async def main():
    logger.init_logging("camera-feed-cleaner", logger.LogLevel.INFO)
    config = Config(
        "config.toml",
        exclude=[
            Module.AUTOBAHN,
            Module.IMAGE_RECOGNITION,
            Module.APRIL_DETECTION,
        ],
    )

    logger.set_log_level(config.log_level)

    nc = await nats.connect(f"nats://localhost:{config.autobahn.port}")
    await nc.subscribe(
        config.camera_feed_cleaner.image_input_topic,
        cb=lambda msg: handle_message(nc, msg, config),
    )
    await nc.flush()
    logger.info("Camera feed cleaner started")


if __name__ == "__main__":
    asyncio.run(main())
