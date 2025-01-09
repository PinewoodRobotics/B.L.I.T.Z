import cv2
import numpy as np

from project.common.config_class.camera_feed_cleaner import CameraConfig


class StereoCameraConfig:
    def __init__(self, K_left, D_left, K_right, D_right, R, T):
        self.camera_matrix_left = np.array(K_left)
        self.dist_coeff_left = np.array(D_left)
        self.camera_matrix_right = np.array(K_right)
        self.dist_coeff_right = np.array(D_right)
        self.rotation = np.array(R)
        self.translation = np.array(T)


def calculate_distance_with_disparity(
    disparity: np.ndarray,
    Q: np.ndarray,
    point: tuple[int, int] | None = None,
    bbox: tuple[int, int, int, int] | None = None,
) -> float | None:
    """
    Calculate distance using disparity and Q matrix, focusing on the most important values.

    Parameters:
    - disparity (np.ndarray): The disparity map.
    - Q (np.ndarray): The reprojection matrix from stereo rectification.
    - point (tuple[int, int]): A specific pixel (x, y) to calculate distance for.
    - bbox (tuple[int, int, int, int]): A bounding box (x, y, width, height) to calculate average distance for.

    Returns:
    - float | None: The calculated distance in meters, or None if disparity is invalid.
    """
    if point is not None:
        # Single point distance calculation
        x, y = point
        disp_value = disparity[y, x]

        if disp_value <= 0:
            # print(f"Invalid disparity at point {point}: {disp_value}")
            return None

        Z = Q[2, 3] / (disp_value + Q[3, 3])
        return Z

    elif bbox is not None:
        # Bounding box average distance calculation, focusing on the most important values
        x, y, w, h = bbox
        roi = disparity[y : y + h, x : x + w]
        valid_disp = roi[roi > 0]  # Consider only positive disparity values

        if valid_disp.size == 0:
            # print(f"No valid disparity values in bounding box {bbox}.")
            return None

        # Filter out smaller values to focus on the most important ones
        filtered_disp = valid_disp[valid_disp > np.mean(valid_disp)]
        if filtered_disp.size == 0:
            print(f"No significant disparity values in bounding box {bbox}.")
            return None

        avg_disp = np.mean(filtered_disp)
        Z = Q[2, 3] / (avg_disp + Q[3, 3])
        return Z

    else:
        raise ValueError("Either a point or bounding box must be provided.")


def cameras_to_disparity_map(
    left_img: np.ndarray,
    right_img: np.ndarray,
    stereo_camera_config: StereoCameraConfig,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    h_left, w_left = left_img.shape[:2]
    h_right, w_right = right_img.shape[:2]

    if h_left != h_right or w_left != w_right:
        right_img = cv2.resize(right_img, (w_left, h_left))

    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(
        stereo_camera_config.camera_matrix_left,
        stereo_camera_config.dist_coeff_left,
        stereo_camera_config.camera_matrix_right,
        stereo_camera_config.dist_coeff_right,
        (w_left, h_left),
        stereo_camera_config.rotation,
        stereo_camera_config.translation,
        flags=cv2.CALIB_ZERO_DISPARITY,
        alpha=0,
    )

    map1_left, map2_left = cv2.initUndistortRectifyMap(
        stereo_camera_config.camera_matrix_left,
        stereo_camera_config.dist_coeff_left,
        R1,
        P1,
        (w_left, h_left),
        cv2.CV_16SC2,
    )
    map1_right, map2_right = cv2.initUndistortRectifyMap(
        stereo_camera_config.camera_matrix_right,
        stereo_camera_config.dist_coeff_right,
        R2,
        P2,
        (w_left, h_left),
        cv2.CV_16SC2,
    )

    rectified_left = cv2.remap(left_img, map1_left, map2_left, cv2.INTER_LINEAR)
    rectified_right = cv2.remap(right_img, map1_right, map2_right, cv2.INTER_LINEAR)

    if len(rectified_left.shape) == 3:
        rectified_left = cv2.cvtColor(rectified_left, cv2.COLOR_BGR2GRAY)
    if len(rectified_right.shape) == 3:
        rectified_right = cv2.cvtColor(rectified_right, cv2.COLOR_BGR2GRAY)

    # Adjust stereo matcher parameters
    stereo_matcher = cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=16 * 8,  # Increase disparity range
        blockSize=15,  # Larger block size
        P1=8 * 3 * 15**2,  # Smoothness penalty
        P2=32 * 3 * 15**2,  # Larger penalty for discontinuities
        uniquenessRatio=10,  # Improve matching confidence
        speckleWindowSize=200,  # Remove noise
        speckleRange=2,
        disp12MaxDiff=1,  # Left-right consistency check
    )

    # Compute disparity
    disparity = (
        stereo_matcher.compute(rectified_left, rectified_right).astype(np.float32)
        / 16.0
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    filled_disparity = cv2.morphologyEx(disparity, cv2.MORPH_CLOSE, kernel)

    # Debug: Check disparity values
    print(f"Disparity min: {np.min(disparity)}, max: {np.max(disparity)}")

    # Normalize for visualization
    normalized_disparity = cv2.normalize(
        disparity, None, 0, 255, cv2.NORM_MINMAX
    ).astype(np.uint8)

    return filled_disparity, normalized_disparity, Q
