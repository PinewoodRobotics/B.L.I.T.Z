import random
import threading
import time
from typing import Callable

import cv2
import numpy as np
import pyapriltags

from blitz.generated.proto.python.sensor.apriltags_pb2 import (
    AprilTagData,
    ProcessedTag,
    UnprocessedTag,
)
from blitz.generated.proto.python.sensor.camera_sensor_pb2 import ImageData, ImageFormat
from blitz.generated.proto.python.sensor.general_sensor_data_pb2 import (
    GeneralSensorData,
    SensorName,
)
from blitz.recognition.position.april.src.camera.OV2311_camera import (
    AbstractCaptureDevice,
)
from blitz.recognition.position.april.src.util import (
    post_process_detection,
    process_image,
    solve_pnp_tag_corners,
    to_float_list,
)


class DetectionCamera:
    def __init__(
        self,
        name: str,
        video_capture: AbstractCaptureDevice,
        tag_size: float,
        detector: pyapriltags.Detector,
        publication_lambda: Callable[[bytes], None],
        publication_image_lambda: Callable[[bytes], None] | None = None,
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

            tag_id_corners_found = post_process_detection(
                process_image(frame, self.detector),
                self.video_capture.get_matrix(),
                self.video_capture.get_dist_coeff(),
            )

            tags_world = []
            for tag in tag_id_corners_found:
                R, t = solve_pnp_tag_corners(
                    tag,
                    self.tag_size,
                    self.video_capture.get_matrix(),
                    self.video_capture.get_dist_coeff(),
                )

                tags_world.append(
                    ProcessedTag(
                        id=tag.id,
                        pose_R=to_float_list(R),
                        pose_t=to_float_list(t),
                    )
                )

            self._publish(frame, tags_world)

    def _publish(self, frame: np.ndarray, found_tags: list[ProcessedTag]):
        data = GeneralSensorData()
        data.sensor_id = self.name
        data.timestamp = int(time.time() * 1000)

        if self.publication_lambda is not None:
            data.sensor_name = SensorName.APRIL_TAGS
            data.apriltags.world_tags.tags.extend(found_tags)

            self.publication_lambda(
                data.SerializeToString(),
            )

        if self.publication_image_lambda is not None:
            data.sensor_name = SensorName.CAMERA
            data.image.image = frame.tobytes()
            data.image.width = frame.shape[1]
            data.image.height = frame.shape[0]
            data.image.format = ImageFormat.GRAY

            self.publication_image_lambda(data.SerializeToString())

    def release(self):
        self.running = False
        self.video_capture.release()
