import numpy as np
from blitz.common.util.math import (
    from_theat_to_3x3_mat,
    get_robot_in_world,
    transform_matrix_to_size,
    transform_vector_to_size,
)


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


def test_transform_matrix_to_size_square():
    matrix = np.eye(6)
    used_diagonals = [True, True, True, True, True, True]
    transformed_matrix = transform_matrix_to_size(used_diagonals, matrix)
    assert np.allclose(transformed_matrix, matrix)


def test_transform_matrix_to_size_nonsq():
    matrix = np.eye(6)
    used_diagonals = [True, True, False, False, False, False]
    transformed_matrix = transform_matrix_to_size(used_diagonals, matrix)
    assert np.allclose(transformed_matrix[0, 0], 1)
    assert np.allclose(transformed_matrix[1, 1], 1)
    assert transformed_matrix.shape[0] == 2


def test_transform_vector_to_size():
    vector = np.array([1, 2, 3, 4, 5, 6])
    used_indices = [True, True, False, False, False, False]
    transformed_vector = transform_vector_to_size(vector, used_indices)
    assert np.allclose(transformed_vector, np.array([1, 2]))


def test_from_theat_to_3x3_mat_90():
    theta = 90
    mat = from_theat_to_3x3_mat(theta)
    assert np.allclose(mat, np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]]))


def test_from_theat_to_3x3_mat_180():
    theta = 180
    mat = from_theat_to_3x3_mat(theta)
    assert np.allclose(mat, np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]))


def test_from_theat_to_3x3_mat_270():
    theta = 270
    mat = from_theat_to_3x3_mat(theta)
    assert np.allclose(mat, np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]]))


def test_from_theat_to_3x3_mat_360():
    theta = 360
    mat = from_theat_to_3x3_mat(theta)
    assert np.allclose(mat, np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]))
