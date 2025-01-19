import numpy as np


def get_rotation_matrix_deg(pitch: float, yaw: float) -> np.ndarray:
    return get_rotation_matrix(np.deg2rad(pitch), np.deg2rad(yaw))


def get_rotation_matrix(pitch: float, yaw: float) -> np.ndarray:
    # First create individual rotation matrices
    pitch_matrix = np.array(
        [
            [np.cos(pitch), 0, np.sin(pitch)],
            [0, 1, 0],
            [-np.sin(pitch), 0, np.cos(pitch)],
        ]
    )

    yaw_matrix = np.array(
        [[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]]
    )

    # Combine the rotations (order matters - here yaw is applied first, then pitch)
    return pitch_matrix @ yaw_matrix


def rotate_vector(vector: np.ndarray, rotation_matrix: np.ndarray) -> np.ndarray:
    return rotation_matrix @ vector


def translate_vector(vector: np.ndarray, translation_vector: np.ndarray) -> np.ndarray:
    return vector + translation_vector


def rotate_pitch_yaw(
    pitch: float, yaw: float, rotation_pitch: float, rotation_yaw: float
) -> tuple[float, float]:
    return pitch + rotation_pitch, yaw + rotation_yaw
