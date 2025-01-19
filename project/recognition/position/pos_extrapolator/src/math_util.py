import numpy as np


def get_rotation_matrix_deg(pitch: float, yaw: float) -> np.ndarray:
    return get_rotation_matrix(np.deg2rad(pitch), np.deg2rad(yaw))


def get_rotation_matrix(pitch: float, yaw: float) -> np.ndarray:
    return np.array(
        [
            [np.cos(pitch), -np.sin(pitch) * np.sin(yaw), -np.sin(pitch) * np.cos(yaw)],
            [np.sin(pitch), np.cos(pitch) * np.sin(yaw), np.cos(pitch) * np.cos(yaw)],
            [0, np.sin(yaw), -np.cos(yaw)],
        ]
    )


def rotate_vector(vector: np.ndarray, rotation_matrix: np.ndarray) -> np.ndarray:
    return rotation_matrix @ vector


def translate_vector(vector: np.ndarray, translation_vector: np.ndarray) -> np.ndarray:
    return vector + translation_vector


def rotate_pitch_yaw(
    pitch: float, yaw: float, rotation_pitch: float, rotation_yaw: float
) -> tuple[float, float]:
    return pitch + rotation_pitch, yaw + rotation_yaw
