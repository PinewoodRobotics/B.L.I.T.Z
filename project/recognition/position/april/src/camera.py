from concurrent.futures import Future, ThreadPoolExecutor
import random
import threading
import time
from typing import Callable
import cv2
import numpy as np
import pyapriltags
from generated.proto.python.AprilTag_pb2 import RawAprilTagCorners
from project.recognition.position.april.src.util import (
    post_process_detection,
    process_image,
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
        name: str,
        video_capture: CaptureDevice,
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
        self.video_capture = video_capture
        self.name = name

        self.running = True
        self.thread = threading.Thread(target=self._update)
        self.thread.daemon = True
        self.thread.start()

    def _update(self):
        matrix = self.video_capture.get_matrix()
        dist_coeff = self.video_capture.get_dist_coeff()
        if matrix is None or dist_coeff is None:
            print("No matrix or dist coeff found!")
            return

        while self.running:
            ret, frame = self.video_capture.get_frame()

            if not ret or frame is None:
                print("No frame found!")
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            found_tags = post_process_detection(
                process_image(gray, self.detector),
                matrix,
                dist_coeff,
            )

            if len(found_tags) > 0:
                self.publication_lambda(
                    RawAprilTagCorners(
                        camera_name=self.name,
                        image_id=random.randint(0, 1000000),
                        timestamp=int(time.time() * 1000),
                        tags=found_tags,
                    ).SerializeToString(),
                )

    def release(self):
        self.running = False
        self.video_capture.release()
