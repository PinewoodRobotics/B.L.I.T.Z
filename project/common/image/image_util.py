import cv2
import numpy as np
from project.generated.project.common.proto.Image_pb2 import ImageMessage


def from_proto_to_cv2(image_message: ImageMessage) -> np.ndarray:
    if not image_message.image:
        raise ValueError("ImageMessage.image is empty")

    buffer_array = np.frombuffer(image_message.image, dtype=np.uint8)
    if buffer_array.size == 0:
        raise ValueError("Failed to convert image buffer to array")

    decoded_image = cv2.imdecode(
        buffer_array,
        cv2.IMREAD_COLOR if not image_message.is_gray else cv2.IMREAD_GRAYSCALE,
    )

    if decoded_image is None:
        raise ValueError(
            "Failed to decode image buffer. Ensure the buffer contains valid encoded image data."
        )

    return decoded_image


def convert_to_gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
