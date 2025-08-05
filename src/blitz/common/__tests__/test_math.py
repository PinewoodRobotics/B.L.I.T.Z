import numpy as np
from blitz.common.util.math import get_robot_in_world


def test_get_robot_in_world():
    # The tag's predicted rotation is erroneous (e.g., 90 degree rotation about Z)
    theta = np.pi / 2
    erroneous_rotation = np.array(
        [
            [np.cos(theta), -np.sin(theta), 0],
            [np.sin(theta), np.cos(theta), 0],
            [0, 0, 1],
        ]
    )
    T_tag_in_camera = np.eye(4)
    T_tag_in_camera[:3, :3] = erroneous_rotation
    T_tag_in_camera[:3, 3] = [1, 2, 3]

    # The camera is at the origin of the robot frame, no rotation
    T_camera_in_robot = np.eye(4)

    # The tag in world is at (10, 0, 0) with no rotation
    T_tag_in_world = np.eye(4)
    T_tag_in_world[:3, 3] = [10, 0, 0]

    # The robot's rotation in world is correct (identity)
    R_robot_rotation_world = np.eye(3)

    T_robot_in_world = get_robot_in_world(
        T_tag_in_camera=T_tag_in_camera,
        T_camera_in_robot=T_camera_in_robot,
        T_tag_in_world=T_tag_in_world,
        R_robot_rotation_world=R_robot_rotation_world,
    )

    assert np.allclose(T_robot_in_world[:3, :3], R_robot_rotation_world)

    T_robot_in_world_error = get_robot_in_world(
        T_tag_in_camera=T_tag_in_camera,
        T_camera_in_robot=T_camera_in_robot,
        T_tag_in_world=T_tag_in_world,
    )
    assert not np.allclose(T_robot_in_world_error[:3, :3], R_robot_rotation_world)
