import numpy as np


def make_rotation_matrix(rotation_matrix: np.ndarray) -> np.ndarray:
    """
    Adjusts the given rotation matrix to account for a new coordinate system
    where the tag position is defined as:

    tag_pos = np.array([
        tag.pose_t[0],
        tag.pose_t[2],
        -tag.pose_t[1],
    ])

    Parameters:
        rotation_matrix (np.ndarray): The original 3x3 rotation matrix.

    Returns:
        np.ndarray: The adjusted 3x3 rotation matrix.
    """
    # Define the transformation matrix for the new coordinate system
    transformation_matrix = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])

    # Apply the transformation to the rotation matrix
    new_rotation_matrix = (
        transformation_matrix @ rotation_matrix @ transformation_matrix.T
    )

    return new_rotation_matrix
