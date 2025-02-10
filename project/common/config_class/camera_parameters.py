import numpy as np
from pydantic import BaseModel


class CameraParametersConfig(BaseModel):
    cameras: list[str]


class CameraParameters(BaseModel):
    camera_matrix: list[list[float]]
    dist_coeff: list[float]
    rotation_vector: list[float]
    translation_vector: list[float]
    port: int

    def get_fxy(self) -> tuple[float, float]:
        return self.camera_matrix[0][0], self.camera_matrix[1][1]

    def get_center(self) -> tuple[float, float]:
        return self.camera_matrix[0][2], self.camera_matrix[1][2]

    def get_dist_coeff(self) -> list[float]:
        return self.dist_coeff

    def get_np_camera_matrix(self) -> np.ndarray:
        return np.array(self.camera_matrix)

    def get_np_dist_coeff(self) -> np.ndarray:
        return np.array(self.dist_coeff)
