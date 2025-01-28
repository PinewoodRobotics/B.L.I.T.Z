import numpy as np


def create_transformation_matrix(
    rotation_matrix: np.ndarray, translation_vector: np.ndarray
) -> np.ndarray:
    transformation_matrix = np.eye(4)
    transformation_matrix[:3, :3] = rotation_matrix
    transformation_matrix[:3, 3] = translation_vector

    return transformation_matrix


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
