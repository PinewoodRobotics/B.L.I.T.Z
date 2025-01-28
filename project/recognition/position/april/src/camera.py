import cv2
import numpy as np
from project.common.config_class.camera_parameters import (
    CameraParameters,
    CameraParametersConfig,
)


class Camera:
    def __init__(self, config: CameraParameters):
        self.config = config
        self.video_capture = cv2.VideoCapture(self.config.port, cv2.CAP_AVFOUNDATION)

        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.video_capture.set(cv2.CAP_PROP_FPS, 100)

    def read(self) -> tuple[bool, np.ndarray]:
        return self.video_capture.read()

    def release(self):
        self.video_capture.release()

    def get_matrix(self) -> np.ndarray:
        return self.config.get_np_camera_matrix()

    def get_dist_coeff(self) -> np.ndarray:
        return self.config.get_np_dist_coeff()
