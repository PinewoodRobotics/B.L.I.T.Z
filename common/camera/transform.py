import cv2
import numpy as np

from common.msg.image import TransformImageMessage


def unfisheye_image(
    image: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeff: np.ndarray,
    do_crop: bool = True,
):
    height, width = image.shape[:2]

    new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(
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

    if do_crop:
        side_crop_percent = 0.2
        top_bottom_crop_percent = 0.2

        side_crop = int(width * side_crop_percent)
        top_bottom_crop = int(height * top_bottom_crop_percent)

        x_start = side_crop
        x_end = width - side_crop
        y_start = top_bottom_crop
        y_end = height - top_bottom_crop

        frame = frame[y_start:y_end, x_start:x_end]

    return frame
