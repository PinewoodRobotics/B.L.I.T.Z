import numpy as np


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
) -> np.ndarray:
    T_tag_in_robot = T_camera_in_robot @ T_tag_in_camera
    T_robot_in_tag = np.linalg.inv(T_tag_in_robot)
    return T_tag_in_world @ T_robot_in_tag


def from_float_list(flat_list: list, rows: int, cols: int) -> np.ndarray:
    if not flat_list or len(flat_list) != rows * cols:
        raise ValueError("The provided list does not match the specified dimensions.")
    return np.array(flat_list).reshape(rows, cols)
