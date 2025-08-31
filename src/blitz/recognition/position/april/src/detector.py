import random
import threading
import time
from typing import Callable

import cv2
import numpy as np
import pyapriltags
from pyapriltags.apriltags import Detector

from blitz.common.camera.image_utils import encode_image
from blitz.common.debug.logger import stats_for_nerds_akit
from blitz.common.debug.replay_recorder import record_image
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
        publication_lambda: Callable[[bytes], None] | None = None,
        publication_image_lambda: Callable[[bytes], None] | None = None,
        record_for_replay: bool = False,
        do_compression: bool = True,
        compression_quality: int = 90,
    ):
        self.detector: Detector = detector
        self.tag_size: float = tag_size
        self.publication_lambda: Callable[[bytes], None] | None = publication_lambda
        self.publication_image_lambda: Callable[[bytes], None] | None = (
            publication_image_lambda
        )
        self.video_capture: AbstractCaptureDevice = video_capture
        self.record_for_replay: bool = record_for_replay
        self.do_compression: bool = do_compression
        self.compression_quality: int = compression_quality

        self.name: str = name

        self.thread: threading.Thread = threading.Thread(target=self._update)
        self.running: bool = True

    def start(self):
        self.thread.daemon = True
        self.thread.start()

    @stats_for_nerds_akit(print_stats=False)
    def _process_tags(self, frame: np.ndarray) -> list[ProcessedTag]:
        tags_world: list[ProcessedTag] = []
        tag_id_corners_found = post_process_detection(
            process_image(frame, self.detector),
            self.video_capture.get_matrix(),
            self.video_capture.get_dist_coeff(),
        )

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

        return tags_world

    def _update(self):
        while self.thread.daemon and self.running:
            ret, frame = self.video_capture.get_frame()

            if not ret or frame is None:
                print("No frame found!")
                continue

            tags_world = []
            if self.publication_image_lambda is not None:
                tags_world = self._process_tags(frame)

            if self.record_for_replay:
                record_image(f"frame-{self.name}", frame)

            self._publish(
                frame, tags_world, self.do_compression, self.compression_quality
            )

    def _publish(
        self,
        frame: np.ndarray,
        found_tags: list[ProcessedTag],
        do_compression: bool = True,
        compression_quality: int = 90,
    ):
        if self.publication_lambda is not None and len(found_tags) > 0:
            data = GeneralSensorData()
            data.sensor_id = self.name
            data.timestamp = int(time.time() * 1000)
            data.sensor_name = SensorName.APRIL_TAGS
            data.apriltags.world_tags.tags.extend(found_tags)

            self.publication_lambda(
                data.SerializeToString(),
            )

        if self.publication_image_lambda is not None:
            data = GeneralSensorData()
            data.sensor_id = self.name
            data.timestamp = int(time.time() * 1000)
            data.image.CopyFrom(
                encode_image(
                    frame, ImageFormat.GRAY, do_compression, compression_quality
                )
            )

            self.publication_image_lambda(data.SerializeToString())

    def release(self):
        self.running = False
        self.video_capture.release()
