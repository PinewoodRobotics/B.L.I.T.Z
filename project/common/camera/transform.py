import cv2
import numpy as np

from project.common.debug import profiler


@profiler.timeit
@profiler.profile_function
def unfisheye_image(
    image: np.ndarray, camera_matrix: np.ndarray, dist_coeff: np.ndarray
):
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

    return dst
