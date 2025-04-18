import time
import cv2
import pytest
from project.recognition.position.april.src.__tests__.util import get_avg_fps
from project.recognition.position.april.src.camera import CaptureDevice
from fixtures.camera_intrinsics import camera_1_matrix, camera_1_dist_coeff


def test_camera_open():
    camera = CaptureDevice(0, 640, 480, 30)
    assert camera.isOpened()


def test_camera_display_w_class():
    camera = CaptureDevice(
        0,
        640,
        480,
        100,
        hard_fps_limit=60,
        camera_matrix=camera_1_matrix,
        dist_coeff=camera_1_dist_coeff,
    )

    last_frame_time = time.time()
    while camera.isOpened():
        ret, frame = camera.get_frame()
        if ret and frame is not None:
            fps = round(1 / (time.time() - last_frame_time), 1)
            cv2.putText(
                frame,
                str(fps),
                (10, 50),
                cv2.FONT_HERSHEY_DUPLEX,
                1.5,
                (0, 255, 0),
                2,
            )

            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            last_frame_time = time.time()
    cv2.destroyAllWindows()


def test_camera_display_without_class():
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # type: ignore
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # type: ignore
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # type: ignore
    camera.set(cv2.CAP_PROP_FPS, 100)  # type: ignore

    last_frame_time = time.time()
    while camera.isOpened():
        ret, frame = camera.read()
        if ret and frame is not None:
            fps = round(1 / (time.time() - last_frame_time), 1)
            cv2.putText(
                frame,
                str(fps),
                (10, 50),
                cv2.FONT_HERSHEY_DUPLEX,
                1.5,
                (0, 255, 0),
                2,
            )

            last_frame_time = time.time()

            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()


def test_camera_fps_30_no_undistortion():
    camera = CaptureDevice(0, 640, 480, 30)
    assert get_avg_fps(camera) == pytest.approx(23, abs=2)


def test_camera_fps_30_with_undistortion():
    camera = CaptureDevice(
        0,
        640,
        480,
        30,
        camera_matrix=camera_1_matrix,
        dist_coeff=camera_1_dist_coeff,
        hard_fps_limit=20,
    )
    assert get_avg_fps(camera) == pytest.approx(20, abs=0.7)
