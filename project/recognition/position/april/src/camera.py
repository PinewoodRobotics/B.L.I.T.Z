import threading
import cv2
import numpy as np
from project.common.config_class.camera_parameters import (
    CameraParameters,
)


## TODO: add a config for removing colors.
class Camera:
    def __init__(self, config: CameraParameters):
        self.config = config

        self.video_capture = cv2.VideoCapture(
            self.config.port, self.config.flags
        )  # AVFOUNDATION = 120
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)  # 640
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)  # 480
        self.video_capture.set(cv2.CAP_PROP_FPS, self.config.max_fps)  # 100

        self.ret, self.frame = self.video_capture.read()

        self.running = True
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def get_frame(self):
        return self.ret, self.frame

    def update(self):
        while self.running:
            self.ret, self.frame = self.video_capture.read()

    def release(self):
        self.running = False
        self.thread.join()
        self.video_capture.release()

    def get_matrix(self) -> np.ndarray:
        return self.config.get_np_camera_matrix()

    def get_dist_coeff(self) -> np.ndarray:
        return self.config.get_np_dist_coeff()
