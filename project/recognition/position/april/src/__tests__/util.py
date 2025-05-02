import os
import time
import cv2
import numpy as np
import pyapriltags

from project.recognition.position.april.src.camera.OV2311_camera import (
    AbstractCaptureDevice,
)
from project.recognition.position.april.src.util import (
    get_map1_and_map2,
    get_undistored_frame,
    py_time_to_fps,
)


def add_cur_dir(path: str):
    return os.path.join(os.path.dirname(__file__), path)


def user_pass_input_selector():
    key = cv2.waitKey(0) & 0xFF
    if key == ord("q"):
        cv2.destroyAllWindows()
        raise Exception("Test terminated by user")
    elif key == ord(" "):
        cv2.destroyAllWindows()


def detector():
    return pyapriltags.Detector(
        families="tag36h11",
        nthreads=1,
        quad_decimate=1.0,
    )


def tag_size():
    return 0.0254


def preprocess_image(image: np.ndarray, matrix: np.ndarray, dist_coeff: np.ndarray):
    map1, map2, new_camera_matrix = get_map1_and_map2(
        matrix, dist_coeff, image.shape[1], image.shape[0]
    )
    return get_undistored_frame(image, map1, map2), new_camera_matrix


def get_avg_fps(device: AbstractCaptureDevice):
    frame_times = []
    last_frame_time = time.time()

    for _ in range(100):
        ret, frame = device.get_frame()
        if not ret or frame is None:
            continue

        current_time = time.time()
        frame_times.append(current_time - last_frame_time)
        last_frame_time = current_time

    avg_time = sum(frame_times) / len(frame_times) if frame_times else 0

    return 1 / avg_time
