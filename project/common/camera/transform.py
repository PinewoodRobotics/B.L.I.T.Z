import cv2
import numpy as np

from project.common import profiler


@profiler.timeit
@profiler.profile_function
def unfisheye_image(
    image: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeff: np.ndarray,
    do_crop: bool = True,
):
    """
    Remove fisheye distortion from an image using camera calibration parameters.

    Args:
        image (np.ndarray): Input image to remove fisheye distortion from
        camera_matrix (np.ndarray): 3x3 camera intrinsic matrix containing focal lengths and optical centers
        dist_coeff (np.ndarray): Distortion coefficients (k1,k2,p1,p2,[k3[,k4,k5,k6]])
        do_crop (bool, optional): Whether to crop edges of output image. Defaults to True.

    Returns:
        np.ndarray: Undistorted image with fisheye effect removed. If do_crop is True,
                   the image edges will be cropped to remove black borders.
    """
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
