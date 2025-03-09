import random
import threading
import time
from typing import Callable
import cv2
import numpy as np
import pyapriltags
from generated.AprilTag_pb2 import AprilTags
from project.common.camera.transform import unfisheye_image
from project.common.config_class.camera_parameters import (
    CameraParameters,
)
from project.recognition.position.april.src.util import from_detection_to_proto


## TODO: add a config for removing colors.
class DetectionCamera:
    def __init__(
        self,
        config: CameraParameters,
        tag_size: float,
        detector: pyapriltags.Detector,
        publication_lambda: Callable[[AprilTags], None],
        publication_image_lambda: Callable[[np.ndarray], None],
    ):
        self.config = config
        self.detector = detector
        self.tag_size = tag_size
        self.publication_lambda = publication_lambda
        self.publication_image_lambda = publication_image_lambda
        
        self.video_capture = cv2.VideoCapture(self.config.port)
        self.video_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG')) # type: ignore
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)  # 640
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)  # 480
        self.video_capture.set(cv2.CAP_PROP_FPS, self.config.max_fps)  # 100

        self.ret, self.frame = self.video_capture.read()
        
        self.last_frame_date = 0

        self.running = True
        self.thread = threading.Thread(target=self._update)
        self.thread.daemon = True
        self.thread.start()

    def get_frame(self):
        return self.ret, self.frame

    def _update(self):
        while self.running:
            self.ret, self.frame = self.video_capture.read()
            
            if not self.ret or time.time() * 1000 - self.last_frame_date < (1000 / self.config.max_fps) - 5:
                continue
            
            self.last_frame_date = time.time() * 1000
            
            
            gray, newcameramtx = self._transform_frame(self.frame)
            found_tags = self.process_image(
                gray,
                self.get_matrix() if newcameramtx is None else newcameramtx,
                self.detector,
                self.tag_size,
                self.config.name,
            )

            if len(found_tags.tags) > 0:
                self.publication_lambda(found_tags)
                print(f"Found {len(found_tags.tags)} tags")

    def _transform_frame(self, frame: np.ndarray, undistort: bool = True):
        new_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        newcameramtx = None
        if undistort:
            new_frame, newcameramtx = unfisheye_image(
                new_frame, self.get_matrix(), self.get_dist_coeff()
            )
        
        return new_frame, newcameramtx

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
        self.running = False
        if hasattr(self, "thread"):
            self.thread.join()
        self.video_capture.release()

    def get_matrix(self) -> np.ndarray:
        return self.config.get_np_camera_matrix()

    def get_dist_coeff(self) -> np.ndarray:
        return self.config.get_np_dist_coeff()
