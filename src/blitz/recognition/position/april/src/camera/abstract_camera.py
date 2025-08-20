import time
from typing import Dict, Type

import numpy as np
from cscore import CvSink, UsbCamera, VideoSource, CvSource

from blitz.common.debug.logger import error, success
from blitz.generated.thrift.config.camera.ttypes import CameraType


class AbstractCaptureDevice:
    _registry: Dict[CameraType, Type["AbstractCaptureDevice"]] = {}

    def __init_subclass__(cls, type: CameraType, **kwargs):
        super().__init_subclass__(**kwargs)
        if type is not None:
            AbstractCaptureDevice._registry[type] = cls

    def __init__(
        self,
        camera_port: int | str,
        width: int,
        height: int,
        max_fps: float,
        camera_matrix: np.ndarray = np.eye(3),
        dist_coeff: np.ndarray = np.zeros(5),
        hard_fps_limit: float | None = None,
        exposure_time: float | None = None,
    ):
        if isinstance(camera_port, str):
            try:
                camera_port = int(camera_port)
            except ValueError:
                pass

        self.port = camera_port
        self.width = width
        self.height = height
        self.max_fps = max_fps
        self.hard_limit = hard_fps_limit
        self.camera_matrix = camera_matrix
        self.dist_coeff = dist_coeff
        self.frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.exposure_time = exposure_time

        self.camera: VideoSource | None = None
        self.sink: CvSink | None = None  # CameraServer.getVideo(self.camera)

        self._is_ready = False
        self._initialize_camera()
        self._last_ts = time.time()

    def _initialize_camera(self):
        self._configure_camera()
        if self.camera:
            self.camera.setConnectionStrategy(
                VideoSource.ConnectionStrategy.kConnectionKeepOpen
            )

            max_attempts = 5
            attempt = 0
            while attempt < max_attempts:
                if self.camera.isConnected() and self.sink is not None:
                    test_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                    ts, _ = self.sink.grabFrame(test_frame)
                    if ts > 0:
                        self._is_ready = True
                        success(f"Camera successfully connected and initialized")
                        return
                attempt += 1
                error(
                    f"Waiting for camera to connect (attempt {attempt}/{max_attempts})..."
                )
                time.sleep(1.0)

            error(f"WARNING: Failed to initialize camera after {max_attempts} attempts")

    def get_frame(self) -> tuple[bool, np.ndarray | None]:
        start = time.time()

        if self.sink is None or not self._is_ready:
            return False, self.frame

        ts, self.frame = self.sink.grabFrame(self.frame)
        now = time.time()

        if ts == 0:
            error_msg = self.sink.getError()
            error(f"Error grabbing frame: {error_msg}")
            self._is_ready = False
            self._initialize_camera()
            self._last_ts = now
            return False, None

        if self.hard_limit:
            interval = 1.0 / self.hard_limit
            took = now - start
            if took < interval:
                time.sleep(interval - took)

        self._last_ts = time.time()

        return True, self.frame

    def release(self):
        self._is_ready = False
        self.sink = None
        self.camera = None

    def get_matrix(self) -> np.ndarray:
        return self.camera_matrix

    def get_dist_coeff(self) -> np.ndarray:
        return self.dist_coeff

    def _configure_camera(self):
        raise NotImplementedError()
