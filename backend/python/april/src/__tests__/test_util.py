import os
from typing import List

import cv2
import numpy as np
import pyapriltags
import pytest

from backend.python.april.src.__tests__.util import add_cur_dir, get_all_generated_tags
from backend.python.april.src.util import (
    post_process_detection,
    process_image,
    solve_pnp_tag_corners,
)


def get_detector():
    return pyapriltags.Detector(
        families="tag36h11",
        nthreads=1,
        quad_decimate=1.0,
        quad_sigma=0.0,
    )


def camera_1_matrix():
    return np.array(
        [
            [450, 0, 400],
            [0, 450, 300],
            [0, 0, 1],
        ]
    )


def camera_1_dist_coeff():
    return np.array(
        [
            0.02421893240091871,
            -0.019483745628435203,
            -0.0002353973963860865,
            0.0010526889774734997,
            -0.032565426732841275,
        ]
    )


def test_detect_tag_corners_cam_1():
    image_path = add_cur_dir("fixtures/images/cam_1_tag_6_37cm_d.png")

    assert os.path.exists(image_path)

    image = cv2.imread(image_path)
    assert image is not None
    detector = get_detector()

    tag_corners = process_image(image, detector)

    assert len(tag_corners) == 1
    assert tag_corners[0].tag_id == 6

    corners_req = [
        [188.87033081, 249.11268616],
        [409.66229248, 244.5305481],
        [404.6394043, 25.74511909],
        [186.49714661, 32.52137756],
    ]

    for i, corner in enumerate(tag_corners[0].corners):
        assert corner[0] == pytest.approx(corners_req[i][0], abs=1)
        assert corner[1] == pytest.approx(corners_req[i][1], abs=1)


def test_post_process_detection_cam_1():
    image_path = add_cur_dir("fixtures/images/cam_1_tag_6_37cm_d.png")
    image = cv2.imread(image_path)
    assert image is not None
    detector = get_detector()
    tag_corners = process_image(image, detector)
    post_processed_tag_corners = post_process_detection(
        tag_corners, camera_1_matrix(), camera_1_dist_coeff()
    )

    assert len(post_processed_tag_corners) == 1
    assert post_processed_tag_corners[0].id == 6

    corners = post_processed_tag_corners[0].corners
    corners_req = [
        [188.87033081, 249.11268616],
        [409.66229248, 244.5305481],
        [404.6394043, 26.74511909],
        [186.49714661, 32.52137756],
    ]

    for i, corner in enumerate(corners):
        assert corner.x == pytest.approx(corners_req[i][0], abs=1)
        assert corner.y == pytest.approx(corners_req[i][1], abs=1)


def test_undistort_point():
    point = np.array([[300, 200]], dtype=np.float32)

    undistorted_point = cv2.undistortPoints(
        point, camera_1_matrix(), camera_1_dist_coeff(), P=camera_1_matrix()
    )

    print(undistorted_point.reshape(2))

    assert undistorted_point[0, 0, 0] == pytest.approx(300, abs=1)
    assert undistorted_point[0, 0, 1] == pytest.approx(200, abs=1)


def test_detected_position_1_cam_1_37cm():
    image_path = add_cur_dir("fixtures/images/cam_1_tag_6_37cm_d.png")
    image = cv2.imread(image_path)
    assert image is not None
    detector = get_detector()

    tag_corners = process_image(image, detector)
    post_processed_tag_corners = post_process_detection(
        tag_corners, camera_1_matrix(), camera_1_dist_coeff()
    )

    assert len(post_processed_tag_corners) == 1
    assert post_processed_tag_corners[0].id == 6

    tag = post_processed_tag_corners[0]
    position = solve_pnp_tag_corners(
        tag, 0.17, camera_1_matrix(), camera_1_dist_coeff()
    )

    assert position[1][0] == pytest.approx(-0.0766, abs=0.01)
    assert position[1][2] == pytest.approx(0.345, abs=0.01)


def test_detected_position_1_cam_1_90cm():
    image_path = add_cur_dir("fixtures/images/cam_1_tag_6_90cm_d.png")
    image = cv2.imread(image_path)
    assert image is not None
    detector = get_detector()

    tag_corners = process_image(image, detector)
    post_processed_tag_corners = post_process_detection(
        tag_corners, camera_1_matrix(), camera_1_dist_coeff()
    )

    assert len(post_processed_tag_corners) == 1
    assert post_processed_tag_corners[0].id == 6

    tag = post_processed_tag_corners[0]
    position = solve_pnp_tag_corners(
        tag, 0.17, camera_1_matrix(), camera_1_dist_coeff()
    )

    assert position[1][0] == pytest.approx(-0.0766, abs=0.003)
    assert position[1][2] == pytest.approx(0.923, abs=0.003)


def test_detected_position_1_cam_1_74cm():
    image_path = add_cur_dir("fixtures/images/cam_1_tag_6_74cm_d.png")
    image = cv2.imread(image_path)
    assert image is not None
    detector = get_detector()

    tag_corners = process_image(image, detector)
    post_processed_tag_corners = post_process_detection(
        tag_corners, camera_1_matrix(), camera_1_dist_coeff()
    )

    assert len(post_processed_tag_corners) == 1
    assert post_processed_tag_corners[0].id == 6

    tag = post_processed_tag_corners[0]
    position = solve_pnp_tag_corners(
        tag, 0.17, camera_1_matrix(), camera_1_dist_coeff()
    )

    assert position[1][0] == pytest.approx(0.44, abs=0.01)
    assert position[1][2] == pytest.approx(0.73, abs=0.01)


def test_generated_tags():
    all_generated_tags = get_all_generated_tags()
    matrix = np.array(
        [
            [691.5, 0, 691.0],
            [0, 691.5, 446.5],
            [0, 0, 1],
        ]
    )
    coeff = np.zeros(5)
    for generated_tag in all_generated_tags:
        detector = get_detector()
        tag_corners = process_image(generated_tag.image, detector)
        post_processed_tag_corners = post_process_detection(tag_corners, matrix, coeff)

        position = solve_pnp_tag_corners(
            post_processed_tag_corners[0], 1, matrix, coeff
        )

        assert len(post_processed_tag_corners) == 1
        assert generated_tag.data.pose.position[0] == pytest.approx(
            position[1][0], abs=0.1
        )
        assert generated_tag.data.pose.position[1] == pytest.approx(
            position[1][1], abs=0.1
        )
        assert generated_tag.data.pose.position[2] == pytest.approx(
            position[1][2], abs=0.1
        )
