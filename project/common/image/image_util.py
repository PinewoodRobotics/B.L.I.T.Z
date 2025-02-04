import cv2
import numpy as np
from generated.Image_pb2 import ImageMessage


def from_proto_to_cv2(image_message: ImageMessage) -> np.ndarray:
    if not image_message.image:
        raise ValueError("ImageMessage.image is empty")

    try:
        # Convert to numpy array (this is still jpg encoded)
        buffer_array = np.frombuffer(image_message.image, dtype=np.uint8)
        if buffer_array.size == 0:
            raise ValueError("Failed to convert image buffer to array")

        # Decode the jpg data
        decoded_image = cv2.imdecode(
            buffer_array,
            cv2.IMREAD_COLOR if not image_message.is_gray else cv2.IMREAD_GRAYSCALE,
        )

        if decoded_image is None:
            raise ValueError(
                f"Failed to decode image buffer. Buffer size: {len(image_message.image)}, Array shape: {buffer_array.shape}"
            )

        return decoded_image
    except Exception as e:
        raise ValueError(f"Error processing image: {str(e)}")
