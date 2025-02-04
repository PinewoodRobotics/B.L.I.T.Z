import cv2
import numpy as np

from generated.Image_pb2 import ImageMessage
from project.common.debug import profiler


@profiler.timeit
@profiler.profile_function
def unfisheye_image(
    image: np.ndarray, camera_matrix: np.ndarray, dist_coeff: np.ndarray
):
    """Undistort (unfisheye) the image using the camera parameters."""
    height, width = image.shape[:2]
    newcameramtx, roi = cv2.getOptimalNewCameraMatrix(
        camera_matrix, dist_coeff, (width, height), 1, (width, height)
    )

    dst = cv2.undistort(image, camera_matrix, dist_coeff, None, newcameramtx)
    x, y, w, h = roi
    dst = dst[y : y + h, x : x + w]

    max_dim = 800
    scale = max_dim / max(dst.shape[0], dst.shape[1])
    if scale < 1:
        dst = cv2.resize(dst, None, fx=scale, fy=scale)

    return (
        dst,
        newcameramtx,
    )


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
