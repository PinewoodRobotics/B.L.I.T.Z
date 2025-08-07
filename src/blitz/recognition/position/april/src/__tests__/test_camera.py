from blitz.common.util.system import SystemStatus, get_system_status
from blitz.recognition.position.april.src.camera.OV2311_camera import OV2311Camera
from blitz.recognition.position.april.src.camera.abstract_camera import (
    AbstractCaptureDevice,
)
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


def calculate_avg_pixel_value(frame: np.ndarray) -> float:
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
