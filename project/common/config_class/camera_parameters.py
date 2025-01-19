import numpy as np
from project.common.config_class.config_template import ConfigTemplate

required_keys_main = ["cameras"]
required_keys_camera = [
    "camera-matrix",
    "dist-coeff",
    "rotation-vector",
    "translation-vector",
]


class CameraParametersConfig(ConfigTemplate):
    def __init__(self, config_raw: dict):
        self.check_config(config_raw, required_keys_main, "CameraParametersConfig")
        self.cameras = config_raw["cameras"]
        self.camera_parameters: dict[str, CameraParameters] = {}

        for camera in self.cameras:
            self.camera_parameters[camera] = CameraParameters(config_raw[camera])


class CameraParameters(ConfigTemplate):
    def __init__(self, config_raw: dict):
        self.check_config(config_raw, required_keys_camera, "CameraParameters")
        self.camera_matrix: list[list[float]] = config_raw["camera-matrix"]
        self.dist_coeff: list[float] = config_raw["dist-coeff"]
        self.rotation_vector: list[float] = config_raw["rotation-vector"]
        self.translation_vector: list[float] = config_raw["translation-vector"]
        self.port: int = config_raw["port"]

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
