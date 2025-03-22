import numpy as np
from pydantic import BaseModel
from typing import List, Tuple


class CameraParameters(BaseModel):
    pi_to_run_on: str
    name: str

    camera_matrix: List[List[float]]
    dist_coeff: List[float]
    port: int

    max_fps: int
    width: int
    height: int
    flags: int

    def get_fxy(self) -> Tuple[float, float]:
        return self.camera_matrix[0][0], self.camera_matrix[1][1]

    def get_center(self) -> Tuple[float, float]:
        return self.camera_matrix[0][2], self.camera_matrix[1][2]

    def get_dist_coeff(self) -> List[float]:
        return self.dist_coeff

    def get_np_camera_matrix(self) -> np.ndarray:
        return np.array(self.camera_matrix)

    def get_np_dist_coeff(self) -> np.ndarray:
        return np.array(self.dist_coeff)
