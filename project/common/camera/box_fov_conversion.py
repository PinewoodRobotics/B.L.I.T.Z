from typing import List, Tuple
import numpy as np


def from_bbox_to_camera_fov(
    bbox: np.ndarray, camera_matrix: np.ndarray
) -> Tuple[float, float, float, float]:
    """
    Convert a bounding box to camera FOV.
    """
    fx = camera_matrix[0, 0]
    fy = camera_matrix[1, 1]
    cx = camera_matrix[0, 2]
    cy = camera_matrix[1, 2]

    x_min, y_min, x_max, y_max = bbox

    yaw_min = np.degrees(np.arctan2(x_min - cx, fx))
    yaw_max = np.degrees(np.arctan2(x_max - cx, fx))
    pitch_min = np.degrees(np.arctan2(y_min - cy, fy))
    pitch_max = np.degrees(np.arctan2(y_max - cy, fy))

    return yaw_min, yaw_max, pitch_min, pitch_max
