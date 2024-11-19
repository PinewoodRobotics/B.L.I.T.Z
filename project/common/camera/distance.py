import cv2
import numpy as np


def judge_distance(
    left_img: np.ndarray,
    right_img: np.ndarray,
    bbox: tuple,
    focal_length: float,
    baseline: float,
    camera_matrix_left: np.ndarray,
    camera_matrix_right: np.ndarray,
    distortion_left: np.ndarray,
    distortion_right: np.ndarray,
    rotation_matrix: np.ndarray,
    translation_vector: np.ndarray,
) -> float | None:
    """
    Calculate the distance to a detected person using stereo vision and save the disparity map as an image.
    """
    try:
        # Unpack bounding box and calculate center
        x1, y1, x2, y2 = bbox
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)

        # Rectify stereo images
        image_size = left_img.shape[:2][::-1]  # (width, height)
        rectify_maps_left = cv2.initUndistortRectifyMap(
            camera_matrix_left,
            distortion_left,
            rotation_matrix,
            camera_matrix_left,
            image_size,
            cv2.CV_16SC2,
        )
        rectify_maps_right = cv2.initUndistortRectifyMap(
            camera_matrix_right,
            distortion_right,
            rotation_matrix,
            camera_matrix_right,
            image_size,
            cv2.CV_16SC2,
        )

        rectified_left = cv2.remap(
            left_img, rectify_maps_left[0], rectify_maps_left[1], cv2.INTER_LINEAR
        )
        rectified_right = cv2.remap(
            right_img, rectify_maps_right[0], rectify_maps_right[1], cv2.INTER_LINEAR
        )

        # Compute disparity map
        stereo = cv2.StereoBM_create(numDisparities=16 * 10, blockSize=15)
        disparity_map = (
            stereo.compute(
                cv2.cvtColor(rectified_left, cv2.COLOR_BGR2GRAY),
                cv2.cvtColor(rectified_right, cv2.COLOR_BGR2GRAY),
            ).astype(np.float32)
            / 16.0
        )

        # Normalize and save the disparity map
        disparity_map_normalized = cv2.normalize(
            disparity_map, None, 0, 255, cv2.NORM_MINMAX
        ).astype(np.uint8)
        cv2.imwrite("disparity_map.jpg", disparity_map_normalized)

        # Validate and fetch disparity value
        if (
            0 <= center_x < disparity_map.shape[1]
            and 0 <= center_y < disparity_map.shape[0]
        ):
            disparity = disparity_map[center_y, center_x]
        else:
            raise ValueError("Computed center point is out of bounds.")

        if disparity > 0:
            return ((focal_length * baseline) / disparity).item()
        else:
            return None

    except Exception as e:
        print(f"Error in judge_distance: {e}")
        return None
