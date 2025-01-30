import numpy as np


def create_transformation_matrix(
    rotation_matrix: np.ndarray, translation_vector: np.ndarray
) -> np.ndarray:
    transformation_matrix = np.eye(4)
    transformation_matrix[:3, :3] = rotation_matrix
    transformation_matrix[:3, 3] = translation_vector

    return transformation_matrix


def get_translation_rotation_components(
    transformation_matrix: np.ndarray,
):
    """
    Extract translation and rotation components from a 4x4 transformation matrix.

    Args:
        transformation_matrix (np.ndarray): 4x4 homogeneous transformation matrix

    Returns:
        tuple: (translation_vector, rotation_matrix)
            - translation_vector (np.ndarray): 3D translation vector
            - rotation_matrix (np.ndarray): 3x3 rotation matrix
    """
    translation = transformation_matrix[:3, 3]
    rotation = transformation_matrix[:3, :3]
    return translation, rotation


def make_transformation_matrix(
    position: np.ndarray,
    direction_vector: np.ndarray,
) -> np.ndarray:
    z_axis = np.array(direction_vector)
    z_axis = z_axis / np.linalg.norm(z_axis)

    x_axis = np.cross(np.array([0, 1, 0]), z_axis)
    x_axis = x_axis / np.linalg.norm(x_axis)

    y_axis = np.cross(z_axis, x_axis)
    y_axis = y_axis / np.linalg.norm(y_axis)

    return create_transformation_matrix(
        np.column_stack((x_axis, y_axis, z_axis)),
        np.array([position[0], position[1], position[2]]),
    )


def get_world_pos(
    T_tag_camera: np.ndarray,
    T_tag_world: np.ndarray,
) -> np.ndarray:
    T_camera_tag = np.linalg.inv(T_tag_camera)
    return np.matmul(T_tag_world, T_camera_tag)


def from_float_list(flat_list: list, rows: int, cols: int) -> np.ndarray:
    if not flat_list or len(flat_list) != rows * cols:
        raise ValueError("The provided list does not match the specified dimensions.")
    return np.array(flat_list).reshape(rows, cols)
