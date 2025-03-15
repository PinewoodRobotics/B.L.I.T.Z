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
    T_camera_robot: np.ndarray,
    T_tag_world: np.ndarray,
) -> np.ndarray:
    """
    Calculate the robot's position in the world frame given:
    - T_tag_camera: Tag's pose in camera frame (from AprilTag detection)
    - T_camera_robot: Camera's pose in robot frame (from calibration)
    - T_tag_world: Tag's pose in world frame (from configuration)

    Note: When the robot turns left, the tag appears to move right in the camera frame.
    We need to invert this to get the correct robot rotation in world frame.
    """
    # First get robot's pose in tag frame
    T_robot_tag = np.linalg.inv(T_tag_camera @ T_camera_robot)
    
    # Then transform to world frame
    # We use T_tag_world to get the final position in world coordinates
    T_robot_world = T_tag_world @ T_robot_tag
    
    # Invert the rotation component to match the actual robot rotation
    # (when robot turns left, tag appears to move right in camera frame)
    R = T_robot_world[:3, :3]
    t = T_robot_world[:3, 3]
    
    # Create the corrected transformation matrix
    T_robot_world_corrected = np.eye(4)
    T_robot_world_corrected[:3, :3] = R.T  # Transpose to invert rotation
    T_robot_world_corrected[:3, 3] = t     # Keep position the same
    
    return T_robot_world_corrected


def from_float_list(flat_list: list, rows: int, cols: int) -> np.ndarray:
    if not flat_list or len(flat_list) != rows * cols:
        raise ValueError("The provided list does not match the specified dimensions.")
    return np.array(flat_list).reshape(rows, cols)
