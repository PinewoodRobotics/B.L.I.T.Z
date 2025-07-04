from enum import Enum
import glob
import os
import platform
import random
import re
import subprocess
import time
import cv2
import numpy as np
import pyapriltags

from blitz.generated.proto.python.sensor.apriltags_pb2 import (
    ProcessedTag,
    UnprocessedTag,
)
from blitz.generated.proto.python.util.vector_pb2 import Vector2


class TagSolvingStrategyTagCorners(Enum):
    CENTER = "center"
    CORNERS = "corners"


def to_float_list(arr: np.ndarray) -> list:
    return list(arr.flatten()) if arr is not None else []


def to_float(val) -> float:
    if isinstance(val, np.ndarray):
        return float(val.item())
    return float(val) if val is not None else 0.0


def from_detection_to_proto_tag(detection: pyapriltags.Detection) -> ProcessedTag:
    if detection.pose_t is None:
        raise ValueError("Detection has no pose data")

    return ProcessedTag(
        id=detection.tag_id,
        pose_R=to_float_list(detection.pose_R) if detection.pose_R is not None else [],
        pose_t=to_float_list(detection.pose_t),
    )


def get_tag_corners_undistorted(
    detection: pyapriltags.Detection,
    camera_matrix: np.ndarray,
    dist_coeff: np.ndarray,
) -> list[Vector2]:
    corners = []
    for corner in detection.corners:
        corner = np.array([[corner[0], corner[1]]], dtype=np.float32)

        corner = cv2.undistortPoints(corner, camera_matrix, dist_coeff, P=camera_matrix)
        corner = corner.reshape(2)

        corners.append(Vector2(x=corner[0], y=corner[1]))

    return corners


def post_process_detection(
    detection: list[pyapriltags.Detection],
    camera_matrix: np.ndarray,
    dist_coeff: np.ndarray,
) -> list[UnprocessedTag]:
    return [
        UnprocessedTag(
            id=det.tag_id,
            corners=get_tag_corners_undistorted(det, camera_matrix, dist_coeff),
        )
        for det in detection
    ]


def from_detection_to_corners_raw(
    detection: pyapriltags.Detection,
) -> list[Vector2]:
    corners = []
    for corner in detection.corners:
        corners.append(Vector2(x=corner[0], y=corner[1]))

    return corners


def process_image(
    image: np.ndarray,
    detector: pyapriltags.Detector,
) -> list[pyapriltags.Detection]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detected_output = detector.detect(gray)
    return detected_output


def get_undistored_frame(
    frame: np.ndarray, map1: np.ndarray, map2: np.ndarray
) -> np.ndarray:
    return cv2.remap(frame, map1, map2, cv2.INTER_LINEAR)


def get_map1_and_map2(
    camera_matrix: np.ndarray,
    dist_coeff: np.ndarray,
    width: int,
    height: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(
        camera_matrix,
        dist_coeff,
        (width, height),
        alpha=0.0,
    )

    map1, map2 = cv2.initUndistortRectifyMap(
        camera_matrix,
        dist_coeff,
        R=np.eye(3),
        newCameraMatrix=new_camera_matrix,
        size=(width, height),
        m1type=cv2.CV_16SC2,
    )

    return map1, map2, new_camera_matrix


def solve_pnp_tag_corners(
    tag_corners: UnprocessedTag,
    tag_size: float,
    camera_matrix: np.ndarray,
    dist_coeff: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Solves the PnP problem for a tag corner.
    Returns:
        - rotation matrix
        - translation vector
    """
    # 1) Define the *unit* square in object space
    #    IPPE_SQUARE expects half-side = 1
    half_size = tag_size / 2
    unit_square = np.array(
        [
            [-half_size, -half_size, 0],
            [half_size, -half_size, 0],
            [half_size, half_size, 0],
            [-half_size, half_size, 0],
        ],
        dtype=np.float32,
    )

    # 2) Pull out your detected image points in the same order
    image_points = np.array([[c.x, c.y] for c in tag_corners.corners], dtype=np.float32)

    # 3) Call the fast square solver
    success, rvec, tvec = cv2.solvePnP(
        unit_square,
        image_points,
        camera_matrix,
        dist_coeff,
        flags=cv2.SOLVEPNP_IPPE,
        useExtrinsicGuess=False,
    )
    if not success:
        raise RuntimeError("solvePnP failed")

    R, _ = cv2.Rodrigues(rvec)
    return R, tvec


def solve_pnp_tags_iterative(
    tags: list[UnprocessedTag],
    tag_size: float,
    camera_matrix: np.ndarray,
    dist_coeff: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    image_points = []
    object_points = []

    half_size = tag_size / 2
    tag_3d_corners = np.array(
        [
            [-half_size, -half_size, 0],  # Bottom-left
            [half_size, -half_size, 0],  # Bottom-right
            [half_size, half_size, 0],  # Top-right
            [-half_size, half_size, 0],  # Top-left
        ]
    )

    for tag in tags:
        for i, corner in enumerate(tag.corners):
            image_points.append([corner.x, corner.y])
            object_points.append(tag_3d_corners[i])

    image_points = np.array(image_points, dtype=np.float32)
    object_points = np.array(object_points, dtype=np.float32)

    _, rvec, tvec = cv2.solvePnP(
        object_points,
        image_points,
        camera_matrix,
        dist_coeff,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )

    return cv2.Rodrigues(rvec)[0], tvec
