import os
from typing import List

import cv2
import numpy as np
import pyapriltags
import pytest

from project.recognition.position.april.src.__tests__.util import (
    add_cur_dir,
    detector,
    preprocess_image,
    tag_size,
    user_pass_input_selector,
)
from project.recognition.position.april.src.util import (
    get_map1_and_map2,
    get_undistored_frame,
    process_image,
)
from fixtures.camera_intrinsics import camera_1_matrix, camera_1_dist_coeff


def test_undistored_frame_camera_1():
    frame = cv2.imread(add_cur_dir("fixtures/undistort/one/f_one_1.png"))

    map1, map2, new_camera_matrix = get_map1_and_map2(
        camera_1_matrix, camera_1_dist_coeff, frame.shape[1], frame.shape[0]
    )

    undistored_frame = get_undistored_frame(frame, map1, map2)
    cv2.imshow("Undistored Frame", undistored_frame)
    user_pass_input_selector()


def test_process_image_camera_1():
    frame = cv2.imread(add_cur_dir("fixtures/position/one/f_one_1.png"))
    undistored_frame, new_camera_matrix = preprocess_image(
        frame, camera_1_matrix, camera_1_dist_coeff
    )

    tags = process_image(
        undistored_frame,
        new_camera_matrix,
        detector(),
        tag_size(),
        "camera_1",
    )

    assert len(tags.tags) == 1
    assert tags.tags[0].tag_id == 0

    tag = tags.tags[0]
    assert tag.position_x_relative == pytest.approx(0, abs=0.1)
    assert tag.position_y_relative == pytest.approx(0, abs=0.1)
    assert tag.position_z_relative == pytest.approx(0.5, abs=0.1)
