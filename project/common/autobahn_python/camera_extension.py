from enum import Enum
import time

import cv2
import numpy as np
from generated.Image_pb2 import ImageMessage
from project.common.autobahn_python.autobahn import Autobahn


class CompressionEnum(Enum):
    MAX_QUALITY = 100
    MEDIUM_QUALITY = 50
    LOW_QUALITY = 10
    PRESERVE_QUALITY = 0


class CameraAutobahnExtension:
    def __init__(
        self,
        autobahn_initialized_instance: Autobahn,
        compression_enum: CompressionEnum,
    ) -> None:
        self.ab = autobahn_initialized_instance
        self.mode = compression_enum

    async def publish_image(self, topic: str, camera_name: str, image_data: np.ndarray):
        """
        Encodes image_data according to self.mode and publishes the resulting bytes.
        """

        if self.mode == CompressionEnum.PRESERVE_QUALITY:
            payload = image_data.tobytes()
        else:
            payload = self._compress_jpeg(image_data, self.mode.value)

        await self.ab.publish(
            topic,
            ImageMessage(
                payload,
                camera_name=camera_name,
                is_gray=False,
                timestamp=int(time.time() * 1000),
                width=image_data.shape[1],
                height=image_data.shape[0],
            ).SerializeToString(),
        )

    def _compress_jpeg(self, image: np.ndarray, quality: int) -> bytes:
        """
        JPEG-encode with given quality (0–100) via OpenCV.
        """

        ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])

        if not ok:
            raise RuntimeError("JPEG encoding failed")
        return buf.tobytes()
