import numpy as np
from blitz.common.util.math import get_robot_in_world

T_robot_world = np.array(
    [
        [-0.95947106, 0.19169274, -0.2065651, 17.76915141],
        [-0.14756189, -0.96622847, -0.21125359, 0.36542339],
        [-0.24008488, -0.17221056, 0.95535478, 18.74622704],
        [0.0, 0.0, 0.0, 1.0],
    ]
)

T_tag_camera = np.array(
    [
        [-0.97359872, 0.04503683, -0.2237794, -0.40760902],
        [0.0144398, -0.96622843, -0.25728211, 0.17366067],
        [-0.22780919, -0.25372085, 0.94006848, 1.2722497],
        [0.0, 0.0, 0.0, 1.0],
    ]
)

T_camera_robot = np.array(
    [
        [0.70710678, 0.0, 0.70710678, -0.4],
        [0.0, 1.0, -0.0, 0.0],
        [-0.70710678, 0.0, 0.70710678, -0.4],
        [0.0, 0.0, 0.0, 1.0],
    ]
)

T_tag_world = np.array(
    [
        [0.7089287, 0.0, -0.70528016, 17.43687501],
        [-0.0, 1.0, -0.0, 0.0],
        [0.70528016, 0.0, 0.7089287, 19.41823473],
        [0.0, 0.0, 0.0, 1.0],
    ]
)


def test_camera_rotations():
    print(get_robot_in_world(T_tag_camera, T_camera_robot, T_tag_world))


if __name__ == "__main__":
    test_camera_rotations()
