from concurrent.futures import Future, ThreadPoolExecutor
import random
import threading
import time
from typing import Callable
import cv2
import numpy as np
import pyapriltags
from generated.AprilTag_pb2 import AprilTags
from generated.status.CameraStatus_pb2 import CameraStatus
from project.common.config_class.camera_parameters import (
    CameraParameters,
)
from project.recognition.position.april.src.util import (
    from_detection_to_proto,
    get_map1_and_map2,
    get_undistored_frame,
    process_image,
    py_time_to_fps,
)


class CaptureDevice(cv2.VideoCapture):
    def __init__(
        self,
        camera,
        width,
        height,
        max_fps,
        camera_matrix=None,
        dist_coeff=None,
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

    def _configure_camera(self):
        if self.isOpened():
            super().release()

        super().__init__(self.port)

        fourcc = cv2.VideoWriter_fourcc(*"MJPG")  # type: ignore
        self.set(cv2.CAP_PROP_FOURCC, fourcc)
        self.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.set(cv2.CAP_PROP_FPS, self.max_fps)

    def get_matrix(self) -> np.ndarray | None:
        return self.camera_matrix

    def get_dist_coeff(self) -> np.ndarray | None:
        return self.dist_coeff


class DetectionCamera:
    def __init__(
        self,
        config: CameraParameters,
        tag_size: float,
        detector: pyapriltags.Detector,
        publication_lambda: Callable[[bytes], None],
        publication_stats_lambda: Callable[[bytes], None] | None = None,
        publication_image_lambda: Callable[[np.ndarray], None] | None = None,
    ):
        self.detector = detector
        self.tag_size = tag_size
        self.publication_lambda = publication_lambda
        self.publication_image_lambda = publication_image_lambda
        self.publication_stats_lambda = publication_stats_lambda
        self.video_capture = CaptureDevice(
            config.camera_path,
            config.width,
            config.height,
            config.max_fps,
            config.get_np_camera_matrix(),
            config.get_np_dist_coeff(),
        )
        self.name = config.name

        self.running = True
        self.thread = threading.Thread(target=self._update)
        self.thread.daemon = True
        self.thread.start()

    def _update(self):
        matrix = self.video_capture.get_matrix()
        while self.running:
            ret, frame = self.video_capture.get_frame()

            if not ret or frame is None:
                print("No frame found!")
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            found_tags = None
            if matrix is not None:
                found_tags = process_image(
                    gray,
                    matrix,
                    self.detector,
                    self.tag_size,
                    self.name,
                )

            if found_tags is not None and len(found_tags.tags) > 0:
                self.publication_lambda(found_tags.SerializeToString())

    def release(self):
        self.running = False
        self.video_capture.release()
