from typing import Optional, cast
import numpy as np
from numpy.typing import NDArray

from blitz.generated.thrift.config.common.ttypes import (
    GenericVector, GenericMatrix)


def get_translation_rotation_components(
    transformation_matrix: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    translation = transformation_matrix[0:3, 3]
    rotation = transformation_matrix[0:3, 0:3]
    return translation, rotation


def normalize_vector(vector: NDArray[np.float64]) -> NDArray[np.float64]:
    return vector / np.linalg.norm(vector)


def make_transformation_matrix_p_d(
    *,
    position: NDArray[np.float64],
    direction_vector: NDArray[np.float64],
    z_axis: NDArray[np.float64] = np.array([0, 0, 1]),
) -> NDArray[np.float64]:
    x_axis = normalize_vector(direction_vector)
    y_axis = normalize_vector(np.cross(z_axis, x_axis))  # pyright: ignore[reportArgumentType]
    return create_transformation_matrix(
        rotation_matrix=np.column_stack((x_axis, y_axis, z_axis)),
        translation_vector=np.array([position[0], position[1], position[2]]),
    )


def create_transformation_matrix(
    *,
    rotation_matrix: NDArray[np.float64],
    translation_vector: NDArray[np.float64],
) -> NDArray[np.float64]:
    transformation_matrix = np.eye(4)
    transformation_matrix[:3, :3] = rotation_matrix
    transformation_matrix[:3, 3] = translation_vector
    return transformation_matrix


# T_bbb_in_aaa = T_###_in_aaa @ T_bbb_in_###
def get_robot_in_world(
    *,
    T_tag_in_camera: NDArray[np.float64],
    T_camera_in_robot: NDArray[np.float64],
    T_tag_in_world: NDArray[np.float64],
    R_robot_rotation_world: NDArray[np.float64] | None = None,
) -> NDArray[np.float64]:
    if R_robot_rotation_world is not None:
        # note this is work in process and, thus, may not work as expected
        # Extract position from tag detection
        tag_position_camera = T_tag_in_camera[:3, 3]

        # Transform tag position to robot frame
        camera_position_robot = T_camera_in_robot[:3, 3]
        camera_rotation_robot = T_camera_in_robot[:3, :3]
        tag_position_robot = (
            camera_position_robot + camera_rotation_robot @ tag_position_camera
        )

        # Transform tag position to world frame using robot's known rotation
        tag_position_world = T_tag_in_world[:3, 3]
        robot_position_world = (
            tag_position_world - R_robot_rotation_world @ tag_position_robot
        )

        return create_transformation_matrix(
            rotation_matrix=R_robot_rotation_world,
            translation_vector=robot_position_world,
        )
    else:
        T_tag_in_robot = T_camera_in_robot @ T_tag_in_camera
        T_robot_in_tag = np.linalg.inv(T_tag_in_robot)
        return T_tag_in_world @ T_robot_in_tag


def swap_rotation_components(*, T_one: NDArray[np.float64], T_two: NDArray[np.float64], R_side_size: int):
    # NOTE: This function swaps the rotation (top-left R_side_size x R_side_size) blocks of T_one and T_two,
    # returning new matrices with the swapped rotation components and all other elements preserved.
    T_one_new = T_one.copy()
    T_two_new = T_two.copy()
    T_one_new[:R_side_size, :R_side_size], T_two_new[:R_side_size, :R_side_size] = (
        T_two[:R_side_size, :R_side_size].copy(),
        T_one[:R_side_size, :R_side_size].copy(),
    )
    return T_one_new, T_two_new


def from_float_list(flat_list: list[float], rows: int, cols: int) -> NDArray[np.float64]:
    if not flat_list or len(flat_list) != rows * cols:
        raise ValueError("The provided list does not match the specified dimensions.")
    return np.array(flat_list).reshape(rows, cols)


def get_np_from_vector(vector: GenericVector) -> NDArray[np.float64]:
    return np.array(vector.values)


def get_np_from_matrix(
    matrix: GenericMatrix,
) -> NDArray[np.float64]:
    return np.array(matrix.values)


def transform_matrix_to_size(
    used_diagonals: list[bool],
    matrix: NDArray[np.float64] = np.eye(6),
) -> NDArray[np.float64]:
    indices = [i for i, used in enumerate(used_diagonals) if used]
    return matrix[indices, :]


def transform_vector_to_size(
    vector: NDArray[np.float64],
    used_indices: list[bool],
) -> NDArray[np.float64]:
    return np.array([v for v, i in zip(vector, used_indices) if i])


def from_theta_to_3x3_mat(theta: float):
    """
    Convert a rotation angle in degrees to a 3x3 rotation matrix.
    Theta is the rotation angle around the z-axis in degrees [0, 360].
    """

    theta_rad = np.deg2rad(theta)
    return np.array(
        [
            [np.cos(theta_rad), -np.sin(theta_rad), 0],
            [np.sin(theta_rad), np.cos(theta_rad), 0],
            [0, 0, 1],
        ]
    )
