import random
import threading
import time
from typing import Callable

import cv2
import numpy as np
import pyapriltags

from generated.proto.python.AprilTag_pb2 import RawAprilTagCorners, TagCorners
from project.recognition.position.april.src.camera.OV2311_camera import (
    AbstractCaptureDevice,
)
from project.recognition.position.april.src.util import (
    post_process_detection,
    process_image,
)


class DetectionCamera:
    def __init__(
        self,
        name: str,
        video_capture: AbstractCaptureDevice,
        tag_size: float,
        detector: pyapriltags.Detector,
        publication_lambda: Callable[[bytes], None],
        publication_image_lambda: Callable[[np.ndarray], None] | None = None,
    ):
        self.detector = detector
        self.tag_size = tag_size
        self.publication_lambda = publication_lambda
        self.publication_image_lambda = publication_image_lambda
        self.video_capture = video_capture

        self.name = name

        self.thread = threading.Thread(target=self._update)

    def start(self):
        self.thread.daemon = True
        self.thread.start()

    def _update(self):
        while self.thread.daemon:
            ret, frame = self.video_capture.get_frame()

            if not ret or frame is None:
                print("No frame found!")
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            found_tags = post_process_detection(
                process_image(gray, self.detector),
                self.video_capture.get_matrix(),
                self.video_capture.get_dist_coeff(),
            )

            self._publish(frame, found_tags)

    def _publish(self, frame: np.ndarray, found_tags: list[TagCorners]):
        if self.publication_image_lambda is not None:
            self.publication_image_lambda(frame)

        if self.publication_lambda is not None and len(found_tags) > 0:
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
