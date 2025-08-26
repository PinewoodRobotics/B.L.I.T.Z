from typing import Optional
import numpy as np

from blitz.generated.thrift.config.common.ttypes import (
    Matrix3x3,
    Matrix4x4,
    Matrix5x5,
    Matrix6x6,
    Vector3D,
    Vector4D,
    Vector5D,
    Vector6D,
)


def get_translation_rotation_components(
    transformation_matrix: np.ndarray,
):
    translation = transformation_matrix[0:3, 3]
    rotation = transformation_matrix[0:3, 0:3]
    return translation, rotation


def normalize_vector(vector: np.ndarray) -> np.ndarray:
    return vector / np.linalg.norm(vector)


def make_transformation_matrix_p_d(
    *,
    position: np.ndarray,
    direction_vector: np.ndarray,
    z_axis: np.ndarray = np.array([0, 0, 1]),
) -> np.ndarray:
    x_axis = normalize_vector(direction_vector)
    y_axis = normalize_vector(np.cross(z_axis, x_axis))
    return create_transformation_matrix(
        rotation_matrix=np.column_stack((x_axis, y_axis, z_axis)),
        translation_vector=np.array([position[0], position[1], position[2]]),
    )


def create_transformation_matrix(
    *,
    rotation_matrix: np.ndarray,
    translation_vector: np.ndarray,
) -> np.ndarray:
    transformation_matrix = np.eye(4)
    transformation_matrix[:3, :3] = rotation_matrix
    transformation_matrix[:3, 3] = translation_vector
    return transformation_matrix


# T_bbb_in_aaa = T_###_in_aaa @ T_bbb_in_###
def get_robot_in_world(
    *,
    T_tag_in_camera: np.ndarray,
    T_camera_in_robot: np.ndarray,
    T_tag_in_world: np.ndarray,
    R_robot_rotation_world: Optional[np.ndarray] = None,
) -> np.ndarray:
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


def swap_rotation_components(*, T_one: np.ndarray, T_two: np.ndarray, R_side_size: int):
    # NOTE: This function swaps the rotation (top-left R_side_size x R_side_size) blocks of T_one and T_two,
    # returning new matrices with the swapped rotation components and all other elements preserved.
    T_one_new = T_one.copy()
    T_two_new = T_two.copy()
    T_one_new[:R_side_size, :R_side_size], T_two_new[:R_side_size, :R_side_size] = (
        T_two[:R_side_size, :R_side_size].copy(),
        T_one[:R_side_size, :R_side_size].copy(),
    )
    return T_one_new, T_two_new


def from_float_list(flat_list: list, rows: int, cols: int) -> np.ndarray:
    if not flat_list or len(flat_list) != rows * cols:
        raise ValueError("The provided list does not match the specified dimensions.")
    return np.array(flat_list).reshape(rows, cols)


def get_np_from_vector(vector: Vector3D | Vector4D | Vector5D | Vector6D) -> np.ndarray:
    """Convert any Vector type to a numpy array."""
    if hasattr(vector, "x") and hasattr(vector, "y") and hasattr(vector, "z"):
        return np.array([vector.x, vector.y, vector.z])  # type: ignore
    elif hasattr(vector, "k1") and hasattr(vector, "k2") and hasattr(vector, "k3"):
        if hasattr(vector, "k4"):
            if hasattr(vector, "k5"):
                if hasattr(vector, "k6"):
                    return np.array(
                        [vector.k1, vector.k2, vector.k3, vector.k4, vector.k5, vector.k6]  # type: ignore
                    )
                return np.array([vector.k1, vector.k2, vector.k3, vector.k4, vector.k5])  # type: ignore
            return np.array([vector.k1, vector.k2, vector.k3, vector.k4])  # type: ignore
        return np.array([vector.k1, vector.k2, vector.k3])  # type: ignore
    else:
        raise ValueError(f"Unsupported vector type: {type(vector)}")


def get_np_from_matrix(
    matrix: Matrix3x3 | Matrix4x4 | Matrix5x5 | Matrix6x6,
) -> np.ndarray:
    """Convert any Matrix type to a numpy array."""
    rows = []
    for i in range(1, 7):
        row_attr = f"r{i}"
        if hasattr(matrix, row_attr):
            vector = getattr(matrix, row_attr)
            vector_array = get_np_from_vector(vector)
            # Reshape to ensure we have a flat vector for each row
            if vector_array.ndim > 1:
                vector_array = vector_array.flatten()
            rows.append(vector_array)
        else:
            break

    if not rows:
        raise ValueError(f"Unsupported matrix type: {type(matrix)}")

    return np.array(rows)


def transform_matrix_to_size(
    used_diagonals: list[bool],
    matrix: np.ndarray = np.eye(6),
) -> np.ndarray:
    indices = [i for i, used in enumerate(used_diagonals) if used]
    return matrix[indices, :]


def transform_vector_to_size(
    vector: np.ndarray,
    used_indices: list[bool],
) -> np.ndarray:
    return np.array([v for v, i in zip(vector, used_indices) if i])


def from_theat_to_3x3_mat(theta: float):
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
