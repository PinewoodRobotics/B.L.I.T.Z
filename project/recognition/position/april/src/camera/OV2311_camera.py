import cv2
import numpy as np
from project.recognition.position.april.src.camera.abstract_camera import (
    AbstractCaptureDevice,
    CamerasEnum,
)


class OV2311Camera(AbstractCaptureDevice, type=CamerasEnum.OV2311):
    def __init__(self, port: int, width: int, height: int, max_fps: int):
        super().__init__(port, width, height, max_fps)

    def _configure_camera(self):
        if self.isOpened():
            super().release()

        super().__super__init__(self.port)

        fourcc = cv2.VideoWriter_fourcc(*"MJPG")  # type: ignore
        self.set(cv2.CAP_PROP_FOURCC, fourcc)
        self.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.set(cv2.CAP_PROP_FPS, self.max_fps)
