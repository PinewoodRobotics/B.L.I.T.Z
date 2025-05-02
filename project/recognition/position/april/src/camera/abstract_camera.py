from enum import Enum
import time
from typing import Dict, Type
import cv2
import numpy as np


class CamerasEnum(Enum):
    OV2311 = "OV2311"


class AbstractCaptureDevice(cv2.VideoCapture):
    """
    This class is a base class for all camera capture devices.
    It provides a common interface for all camera capture devices.

    NOTE: This class is meant to be used as an extension of a new class. THE _configure_camera method is not implemented in this class by default.
    """

    _registry: Dict[CamerasEnum, Type["AbstractCaptureDevice"]] = {}

    def __init_subclass__(cls, type: CamerasEnum, **kwargs):
        super().__init_subclass__(**kwargs)
        if type is not None:
            AbstractCaptureDevice._registry[type] = cls

    @classmethod
    def get_registry(cls) -> Dict[CamerasEnum, Type["AbstractCaptureDevice"]]:
        return cls._registry

    def __init__(
        self,
        camera,
        width,
        height,
        max_fps,
        camera_matrix=np.eye(3),
        dist_coeff=np.zeros(5),
        hard_fps_limit=None,
    ):
        super().__init__(camera)
        self.port = camera
        self.width = width
        self.height = height
        self.max_fps = max_fps
        self.hard_limit = hard_fps_limit

        self.camera_matrix = camera_matrix
        self.dist_coeff = dist_coeff

        self._configure_camera()
        self._last_ts = time.time()

    def __super__init__(self, port: int):
        super().__init__(port)

    def get_frame(self) -> tuple[bool, np.ndarray | None]:
        start = time.time()

        ret, frame = super().read()
        now = time.time()
        if not ret or frame is None:
            self._configure_camera()
            self._last_ts = now
            return False, None

        if self.hard_limit:
            interval = 1.0 / self.hard_limit
            took = now - start
            if took < interval:
                time.sleep(interval - took)

        self._last_ts = time.time()
        return True, frame

    def release(self):
        super().release()

    def get_matrix(self) -> np.ndarray:
        return self.camera_matrix

    def get_dist_coeff(self) -> np.ndarray:
        return self.dist_coeff

    def _configure_camera(self):
        raise NotImplementedError()
