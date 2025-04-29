import os
from typing import List

import cv2
import numpy as np
import pyapriltags
import pytest

from generated.proto.python.AprilTag_pb2 import Corner, TagCorners
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
    post_process_detection,
    process_image,
    solve_pnp_tag_corners,
    solve_pnp_tags_iterative,
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


"""
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
"""


def test_detect_tag_corners_cam_1():
    image_path = add_cur_dir("fixtures/position/one/photo_20250429_000854.png")

    assert os.path.exists(image_path)

    image = cv2.imread(image_path)
    detector = pyapriltags.Detector(
        families="tag36h11",
        nthreads=1,
        quad_decimate=1.0,
    )

    tag_corners = process_image(image, detector)

    assert len(tag_corners) == 1
    assert tag_corners[0].tag_id == 6

    assert tag_corners[0].corners[0][0] == pytest.approx(325.20846558, abs=0.1)
    assert tag_corners[0].corners[0][1] == pytest.approx(290.58465576, abs=0.1)
    assert tag_corners[0].corners[1][0] == pytest.approx(407.68933105, abs=0.1)
    assert tag_corners[0].corners[1][1] == pytest.approx(288.7762146, abs=0.1)
    assert tag_corners[0].corners[2][0] == pytest.approx(405.90567017, abs=0.1)
    assert tag_corners[0].corners[2][1] == pytest.approx(206.53056335, abs=0.1)
    assert tag_corners[0].corners[3][0] == pytest.approx(323.26226807, abs=0.1)
    assert tag_corners[0].corners[3][1] == pytest.approx(208.2794342, abs=0.1)


def test_post_process_detection_cam_1():
    image_path = add_cur_dir("fixtures/position/one/photo_20250429_000854.png")
    image = cv2.imread(image_path)
    detector = pyapriltags.Detector(
        families="tag36h11",
        nthreads=1,
        quad_decimate=1.0,
    )
    tag_corners = process_image(image, detector)
    post_processed_tag_corners = post_process_detection(
        tag_corners, camera_1_matrix, camera_1_dist_coeff
    )

    assert len(post_processed_tag_corners) == 1
    assert post_processed_tag_corners[0].id == 6

    corners = post_processed_tag_corners[0].corners
    assert corners[0].x == pytest.approx(325.20846558, abs=0.1)
    assert corners[0].y == pytest.approx(290.58465576, abs=0.1)
    assert corners[1].x == pytest.approx(407.68933105, abs=0.1)
    assert corners[1].y == pytest.approx(288.7762146, abs=0.1)
    assert corners[2].x == pytest.approx(405.80567017, abs=0.1)
    assert corners[2].y == pytest.approx(206.53056335, abs=0.1)
    assert corners[3].x == pytest.approx(323.26226807, abs=0.1)
    assert corners[3].y == pytest.approx(208.2794342, abs=0.1)


def test_undistort_point():
    point = np.array([[300, 200]], dtype=np.float32)

    undistorted_point = cv2.undistortPoints(
        point, camera_1_matrix, camera_1_dist_coeff, P=camera_1_matrix
    )

    print(undistorted_point.reshape(2))

    assert undistorted_point[0, 0, 0] == pytest.approx(300, abs=0.1)
    assert undistorted_point[0, 0, 1] == pytest.approx(200, abs=0.1)


def test_detected_position_cam_1():
    image_path = add_cur_dir("fixtures/position/one/photo_20250429_000854.png")
    image = cv2.imread(image_path)
    detector = pyapriltags.Detector(
        families="tag36h11",
        nthreads=1,
        quad_decimate=1.0,
    )

    tag_corners = process_image(image, detector)
    post_processed_tag_corners = post_process_detection(
        tag_corners, camera_1_matrix, camera_1_dist_coeff
    )

    assert len(post_processed_tag_corners) == 1
    assert post_processed_tag_corners[0].id == 6

    tag = post_processed_tag_corners[0]
    position = solve_pnp_tag_corners(tag, 17, camera_1_matrix, camera_1_dist_coeff)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    fx, fy, cx, cy = (
        camera_1_matrix[0, 0],
        camera_1_matrix[1, 1],
        camera_1_matrix[0, 2],
        camera_1_matrix[1, 2],
    )
    detected_output = detector.detect(
        gray,
        estimate_tag_pose=True,
        tag_size=17,
        camera_params=(fx, fy, cx, cy),
    )
    print(detected_output[0].pose_t)

    print(position[1])

    assert position[1][0] == pytest.approx(0.05, abs=0.01)
    assert position[1][1] == pytest.approx(0.35, abs=0.01)


def test_solve_pnp_tag_corners():
    tag_corners = TagCorners(
        id=0,
        corners=[
            Corner(x=300, y=300),
            Corner(x=350, y=300),
            Corner(x=350, y=250),
            Corner(x=300, y=250),
        ],
    )

    tag_size = 0.5

    camera_matrix = np.array(
        [[600, 0, 320], [0, 600, 240], [0, 0, 1]], dtype=np.float64
    )

    dist_coeff = np.zeros((5, 1), dtype=np.float64)  # no distortion

    R, tvec = solve_pnp_tag_corners(tag_corners, tag_size, camera_matrix, dist_coeff)

    assert R.shape == (3, 3)
    assert tvec.shape == (3, 1)

    assert R[0, 0] == pytest.approx(1.0, abs=0.01)
    assert R[1, 1] == pytest.approx(-1.0, abs=0.01)
    assert R[2, 2] == pytest.approx(-1.0, abs=0.01)

    assert tvec[0, 0] == pytest.approx(0.05, abs=0.01)
    assert tvec[1, 0] == pytest.approx(0.35, abs=0.01)
    assert tvec[2, 0] == pytest.approx(6.0, abs=0.1)
