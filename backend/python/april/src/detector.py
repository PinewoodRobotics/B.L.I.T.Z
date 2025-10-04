import random
import threading
import time
from typing import Callable

import cv2
import numpy as np
from numpy.typing import NDArray
import pyapriltags
from pyapriltags.apriltags import Detector

from backend.python.april.src.camera.abstract_camera import AbstractCaptureDevice
from backend.python.april.src.util import (
    convert_to_wpi_position,
    convert_to_wpi_rotation,
    post_process_detection,
    process_image,
    solve_pnp_tag_corners,
    to_float_list,
)
from backend.python.common.camera.image_utils import encode_image
from backend.python.common.debug.logger import stats_for_nerds_akit
from backend.python.common.debug.replay_recorder import record_image
from backend.generated.proto.python.sensor.apriltags_pb2 import (
    AprilTagData,
    ProcessedTag,
    UnprocessedTag,
)
from backend.generated.proto.python.sensor.camera_sensor_pb2 import (
    ImageData,
    ImageFormat,
)
from backend.generated.proto.python.sensor.general_sensor_data_pb2 import (
    GeneralSensorData,
    SensorName,
)
from backend.generated.proto.python.util.position_pb2 import Rotation3d
from backend.generated.proto.python.util.vector_pb2 import Vector3


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

        self.thread: threading.Thread = threading.Thread(target=self._run_loop)
        self.running: bool = True

    def start(self):
        self.thread.daemon = True
        self.thread.start()

    # @stats_for_nerds_akit(print_stats=False)
    def _process_tags(self, frame: NDArray[np.uint8]) -> list[ProcessedTag]:
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
                    positionWPILib=convert_to_wpi_position(t),
                    rotationWPILib=convert_to_wpi_rotation(R),
                )
            )

        return tags_world

    def _run_loop(self):
        while self.thread.daemon and self.running:
            ret, frame = self.video_capture.get_frame()
            start_time = time.time()

            if not ret or frame is None:
                print("No frame found!")
                continue

            tags_world = []
            if self.publication_image_lambda is not None:
                tags_world = self._process_tags(frame)

            if self.record_for_replay:
                record_image(f"frame-{self.name}", frame)

            processing_time = time.time() - start_time
            self._publish(
                frame,
                tags_world,
                processing_time,
                self.do_compression,
                self.compression_quality,
            )

    def _publish(
        self,
        frame: NDArray[np.uint8],
        found_tags: list[ProcessedTag],
        processing_time: float,
        do_compression: bool = True,
        compression_quality: int = 90,
    ):
        if self.publication_lambda is not None and len(found_tags) > 0:
            data = GeneralSensorData()
            data.sensor_id = self.name
            data.timestamp = int(time.time() * 1000)
            data.sensor_name = SensorName.APRIL_TAGS
            data.apriltags.world_tags.tags.extend(found_tags)
            data.processing_time_ms = int(processing_time * 1000)
            self.publication_lambda(
                data.SerializeToString(),
            )

        if self.publication_image_lambda is not None:
            data = GeneralSensorData()
            data.sensor_name = SensorName.CAMERA
            data.sensor_id = self.name
            data.timestamp = int(time.time() * 1000)
            data.processing_time_ms = int(processing_time * 1000)
            data.image.CopyFrom(
                encode_image(
                    frame, ImageFormat.GRAY, do_compression, compression_quality
                )
            )

            self.publication_image_lambda(data.SerializeToString())

    def release(self):
        self.running = False
        self.video_capture.release()
