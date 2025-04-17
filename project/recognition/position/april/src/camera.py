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
)


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
        self.config = config
        self.detector = detector
        self.tag_size = tag_size

        self.publication_lambda = publication_lambda
        self.publication_image_lambda = publication_image_lambda
        self.publication_stats_lambda = publication_stats_lambda

        self.port = self.config.camera_path

        if self.port is None:
            raise ValueError(
                f"Camera with hardware id {self.config.camera_path} not found"
            )

        self.create_camera()

        self.last_frame_date = time.time()
        self.frame_counter = 0

        self.map1, self.map2, self.new_camera_matrix = get_map1_and_map2(
            self.get_matrix(),
            self.get_dist_coeff(),
            self.config.width,
            self.config.height,
        )

        self.running = True
        self.thread = threading.Thread(target=self._update)
        self.thread.daemon = True
        self.thread.start()

    def create_camera(self):
        self.video_capture = cv2.VideoCapture(self.config.camera_path)
        print(f"Opening camera on port {self.port}: {self.video_capture.isOpened()}")
        self.video_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # type: ignore

        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)  # 640
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)  # 480
        self.video_capture.set(cv2.CAP_PROP_FPS, self.config.max_fps)

    def get_frame(self):
        return self.ret, self.frame

    def _update(self):
        while self.running:
            self.ret, self.frame = self.video_capture.read()

            if time.time() * 1000 - self.last_frame_date < 1000 / self.config.max_fps:
                continue
            self.last_frame_date = time.time() * 1000

            if not self.ret or self.frame is None:
                print("No frame found")
                self.create_camera()
                continue

            new_frame = get_undistored_frame(self.frame, self.map1, self.map2)
            gray = cv2.cvtColor(new_frame, cv2.COLOR_BGR2GRAY)
            found_tags = process_image(
                gray,
                self.get_matrix_after_remap(),
                self.detector,
                self.tag_size,
                self.config.name,
            )

            if len(found_tags.tags) > 0:
                self.publication_lambda(found_tags.SerializeToString())

    def release(self):
        print(f"Releasing camera on port {self.port}")
        self.running = False
        self.video_capture.release()

    def get_matrix(self) -> np.ndarray:
        return self.config.get_np_camera_matrix()

    def get_matrix_after_remap(self) -> np.ndarray:
        return self.new_camera_matrix

    def get_dist_coeff(self) -> np.ndarray:
        return self.config.get_np_dist_coeff()
