import cv2
import numpy as np
from generated.common.proto.Image_pb2 import ImageMessage


def from_proto_to_cv2(image_message: ImageMessage) -> np.ndarray:
    return cv2.imdecode(
        np.frombuffer(image_message.image, dtype=np.uint8),
        cv2.IMREAD_COLOR if not image_message.is_gray else cv2.IMREAD_GRAYSCALE,
    )


def convert_to_gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
