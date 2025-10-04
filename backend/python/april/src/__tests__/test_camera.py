import cv2
from numpy.typing import NDArray
from backend.python.april.src.__tests__.util import add_cur_dir
from backend.python.april.src.camera import ReplayCamera
from backend.python.april.src.camera.OV2311_camera import OV2311Camera
from backend.python.common.debug.replay_recorder import (
    close,
    get_next_key_replay,
    init_replay_recorder,
    record_image,
)
from backend.python.common.util.system import SystemStatus, get_system_status
from backend.generated.proto.python.sensor.camera_sensor_pb2 import ImageFormat
import numpy as np


def test_camera_open():
    if get_system_status() != SystemStatus.DEVELOPMENT:
        return

    video_capture = OV2311Camera(
        camera_port="/dev/video0",
        width=800,
        height=600,
        max_fps=30,
        camera_matrix=np.eye(3),
        dist_coeff=np.zeros(5),
    )
    frames = []
    for i in range(10):
        frame = video_capture.get_frame()
        frames.append(frame)

    assert len(frames) == 10

    video_capture.release()


def calculate_avg_pixel_value(frame: NDArray[np.uint8]) -> float:
    return float(np.mean(frame))


def test_camera_exposure_time():
    if get_system_status() != SystemStatus.DEVELOPMENT:
        return

    video_capture = OV2311Camera(
        camera_port="/dev/video0",
        width=800,
        height=600,
        max_fps=30,
        camera_matrix=np.eye(3),
        dist_coeff=np.zeros(5),
        exposure_time=20,
    )
    frames = []
    for i in range(10):
        frame = video_capture.get_frame()
        frames.append(frame)

    assert len(frames) == 10
    avg_pixel_values = np.array(
        [calculate_avg_pixel_value(frame) for frame in frames]
    ).mean()

    assert avg_pixel_values > 200

    video_capture.release()


def test_camera_replay():
    init_replay_recorder(add_cur_dir("fixtures/replay.db"), mode="w")
    frames = [
        add_cur_dir("fixtures/images/cam_1_tag_6_37cm_d.png"),
        add_cur_dir("fixtures/images/cam_1_tag_6_74cm_d.png"),
        add_cur_dir("fixtures/images/cam_1_tag_6_90cm_d.png"),
    ]
    images = []
    for frame in frames:
        image = cv2.imread(frame, cv2.IMREAD_COLOR_RGB)
        images.append(image)
        record_image(
            "camera",
            image,  # pyright: ignore[reportArgumentType]
            format=ImageFormat.RGB,
            do_compress=True,
            compression_quality=20,
        )

    close()

    init_replay_recorder(add_cur_dir("fixtures/replay.db"), mode="r")

    video_capture = ReplayCamera.ReplayCamera(camera_topic="camera")
    for i in range(3):
        frame = video_capture.get_frame()
        if not frame[0] or frame[1] is None:
            raise Exception("Failed to get frame")

    assert not video_capture.get_frame()[0]

    video_capture.release()
