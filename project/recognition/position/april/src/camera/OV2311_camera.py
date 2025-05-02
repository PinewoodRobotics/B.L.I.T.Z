import cv2
from project.recognition.position.april.src.camera.abstract_camera import (
    AbstractCaptureDevice,
    CameraType,
)


class OV2311Camera(AbstractCaptureDevice, type=CameraType.OV2311):
    def _configure_camera(self):
        if self.isOpened():
            super().release()

        super().__super__init__(self.port)

        fourcc = cv2.VideoWriter_fourcc(*"MJPG")  # type: ignore
        self.set(cv2.CAP_PROP_FOURCC, fourcc)
        self.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.set(cv2.CAP_PROP_FPS, self.max_fps)
