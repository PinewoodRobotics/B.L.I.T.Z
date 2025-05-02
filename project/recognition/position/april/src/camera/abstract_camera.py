from enum import Enum
import time
from typing import Dict, Type
import cv2
import numpy as np

from generated.thrift.config.camera.ttypes import CameraType


class AbstractCaptureDevice(cv2.VideoCapture):
    """
    This class is a base class for all camera capture devices.
    It provides a common interface for all camera capture devices.

    NOTE: This class is meant to be used as an extension of a new class. THE _configure_camera method is not implemented in this class by default.
    """

    _registry: Dict[CameraType, Type["AbstractCaptureDevice"]] = {}

    def __init_subclass__(cls, type: CameraType, **kwargs):
        super().__init_subclass__(**kwargs)
        if type is not None:
            AbstractCaptureDevice._registry[type] = cls

    @classmethod
    def get_registry(cls) -> Dict[CameraType, Type["AbstractCaptureDevice"]]:
        return cls._registry

    def __init__(
        self,
        camera_port: int | str,
        width: int,
        height: int,
        max_fps: float,
        camera_matrix: np.ndarray = np.eye(3),
        dist_coeff: np.ndarray = np.zeros(5),
        hard_fps_limit: float | None = None,
    ):
        if isinstance(camera_port, str):
            try:
                camera_port = int(camera_port)
            except ValueError:
                pass

        super().__init__(camera_port)
        self.port = camera_port
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
