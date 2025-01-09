import numpy as np
from project.common.camera.box_fov_conversion import (
    determine_lidar_oriented_bbox,
    from_bbox_to_camera_fov,
)


def test_from_bbox_to_camera_fov():
    # Define a sample camera matrix (fx, fy, cx, cy)
    camera_matrix = np.array(
        [
            [800, 0, 320],  # fx = 800, cx = 320
            [0, 800, 240],  # fy = 800, cy = 240
            [0, 0, 1],  # homogenous coordinates
        ]
    )

    # Define a bounding box (x_min, y_min, x_max, y_max)
    bbox = np.array([100, 150, 500, 400])

    # Expected values (manually calculated or known test data)
    expected_yaw_min = np.degrees(np.arctan2(100 - 320, 800))
    expected_yaw_max = np.degrees(np.arctan2(500 - 320, 800))
    expected_pitch_min = np.degrees(np.arctan2(150 - 240, 800))
    expected_pitch_max = np.degrees(np.arctan2(400 - 240, 800))

    expected = (
        expected_yaw_min,
        expected_yaw_max,
        expected_pitch_min,
        expected_pitch_max,
    )

    # Call the function with test data
    result = from_bbox_to_camera_fov(bbox, camera_matrix)

    print(result)

    # Assert the result matches the expected values
    assert np.allclose(
        result, expected, atol=1e-5
    ), f"Expected {expected}, but got {result}"


def test_determine_lidar_oriented_bbox():
    bbox_fov = (-30, 30, -15, 15)
    # Camera is only slightly forward along the Z-axis
    camera_translation_3D = np.array([0.0, 0.0, 1.0])  # Forward movement only
    camera_rotation_3D = np.eye(3)

    expected = (-29.0, 31.0, -14.0, 16.0)  # Adjusted expected values
    result = determine_lidar_oriented_bbox(
        bbox_fov, camera_translation_3D, camera_rotation_3D
    )

    assert np.allclose(result, expected, atol=0.1), f"Expected {expected}, got {result}"
