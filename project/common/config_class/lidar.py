import numpy as np
from pydantic import BaseModel

from project.common.util.math import make_transformation_matrix_p_d


class LidarConfig(BaseModel):
    pi_to_run_on: str

    port: str
    baudrate: int
    name: str
    is_2d: bool

    min_distance_meters: float
    max_distance_meters: float

    position_in_robot: list[float]
    rotation_in_robot: list[float]

    @property
    def transformation(self) -> np.ndarray:
        return make_transformation_matrix_p_d(
            np.array(self.position_in_robot),
            np.array([-x for x in self.rotation_in_robot]),
        )
