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
)


class DetectionCamera:
    def __init__(
        self,
        config: CameraParameters,
        tag_size: float,
        detector_builder: Callable[[], pyapriltags.Detector],
        publication_lambda: Callable[[bytes], None],
        publication_stats_lambda: Callable[[bytes], None] | None = None,
        publication_image_lambda: Callable[[np.ndarray], None] | None = None,
    ):
        self.config = config
        self.detector_builder = detector_builder
        self.detector = detector_builder()
        self.tag_size = tag_size
        self.publication_lambda = publication_lambda
        self.publication_image_lambda = publication_image_lambda
        self.publication_stats_lambda = publication_stats_lambda

        self.port = self.config.camera_path

        if self.port is None:
            raise ValueError(
                f"Camera with hardware id {self.config.camera_path} not found"
            )

        self.create_camera(self.config)

        self.ret, self.frame = self.video_capture.read()

        self.last_frame_date = 0
        self.frame_counter = 0

        self.running = True
        self.thread = threading.Thread(target=self._update)
        self.thread.daemon = True
        self.thread.start()

    def create_camera(self, config: CameraParameters):
        self.config = config
        self.video_capture = cv2.VideoCapture(config.camera_path)
        print(f"Opening camera on port {self.port}: {self.video_capture.isOpened()}")
        self.video_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # type: ignore
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)  # 640
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)  # 480
        self.video_capture.set(cv2.CAP_PROP_FPS, self.config.max_fps)

    def get_frame(self):
        return self.ret, self.frame

    def _update(self):
        while self.running:
            start_time = time.time() * 1000
            self.ret, self.frame = self.video_capture.read()

            if not self.ret or self.frame is None:
                print("No frame found")
                self.create_camera(self.config)
                continue

            start_time_inference = time.time() * 1000
            new_frame = cv2.undistort(
                self.frame, self.get_matrix(), self.get_dist_coeff()
            )

            if self.publication_image_lambda is not None:
                self.publication_image_lambda(new_frame)

            gray = cv2.cvtColor(new_frame, cv2.COLOR_BGR2GRAY)
            found_tags = self.process_image(
                gray,
                self.get_matrix(),
                self.detector,
                self.tag_size,
                self.config.name,
            )

            if len(found_tags.tags) > 0:
                self.publication_lambda(found_tags.SerializeToString())

            if self.publication_stats_lambda is not None:
                end_time = time.time() * 1000
                self.publication_stats_lambda(
                    CameraStatus(
                        name=self.config.name,
                        frame_time=end_time - start_time,
                        inference_time=end_time - start_time_inference,
                    ).SerializeToString()
                )

    def process_image(
        self,
        image: np.ndarray,
        camera_matrix: np.ndarray,
        detector: pyapriltags.Detector,
        tag_size: float,
        camera_name: str,
    ):
        fx, fy, cx, cy = (
            camera_matrix[0, 0],
            camera_matrix[1, 1],
            camera_matrix[0, 2],
            camera_matrix[1, 2],
        )

        output = AprilTags(
            camera_name=camera_name,
            image_id=random.randint(0, 1000000),
            tags=[
                from_detection_to_proto(tag)
                for tag in detector.detect(
                    image,
                    estimate_tag_pose=True,
                    camera_params=((fx, fy, cx, cy)),
                    tag_size=tag_size,
                )
            ],
            timestamp=int(time.time() * 1000),
        )

        return output

    def release(self):
        print(f"Releasing camera on port {self.port}")
        self.running = False
        self.video_capture.release()

    def get_matrix(self) -> np.ndarray:
        return self.config.get_np_camera_matrix()

    def get_dist_coeff(self) -> np.ndarray:
        return self.config.get_np_dist_coeff()
