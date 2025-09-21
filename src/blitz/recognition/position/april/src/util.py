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
from numpy.typing import NDArray
from typing import cast
import pyapriltags

from blitz.common.util.math import get_np_from_matrix, get_np_from_vector
from blitz.generated.proto.python.sensor.apriltags_pb2 import (
    ProcessedTag,
    UnprocessedTag,
)
from blitz.generated.proto.python.util.position_pb2 import Rotation3d
from blitz.generated.proto.python.util.vector_pb2 import Vector2, Vector3
from blitz.generated.thrift.config.apriltag.ttypes import AprilDetectionConfig
from blitz.generated.thrift.config.camera.ttypes import CameraParameters, CameraType
from blitz.recognition.position.april.src.camera.OV2311_camera import OV2311Camera
from blitz.recognition.position.april.src.camera.abstract_camera import (
    AbstractCaptureDevice,
)


class TagSolvingStrategyTagCorners(Enum):
    CENTER = "center"
    CORNERS = "corners"


def to_float_list(arr: NDArray[np.float64]) -> list[float]:
    return list(arr.flatten())


def to_float(val: NDArray[np.float64] | float | int | None) -> float:
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
    camera_matrix: NDArray[np.float64],
    dist_coeff: NDArray[np.float64],
) -> list[Vector2]:
    corners: list[Vector2] = []
    for corner in detection.corners:
        corner = np.array([[corner[0], corner[1]]], dtype=np.float32)

        corner = cv2.undistortPoints(corner, camera_matrix, dist_coeff, P=camera_matrix)
        corner = corner.reshape(2)

        corners.append(Vector2(x=corner[0], y=corner[1]))

    return corners


def post_process_detection(
    detection: list[pyapriltags.Detection],
    camera_matrix: NDArray[np.float64],
    dist_coeff: NDArray[np.float64],
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
    corners: list[Vector2] = []
    for corner in detection.corners:
        corners.append(Vector2(x=corner[0], y=corner[1]))

    return corners


def process_image(
    image: NDArray[np.uint8],
    detector: pyapriltags.Detector,
) -> list[pyapriltags.Detection]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detected_output = detector.detect(gray)
    return detected_output


def get_undistored_frame(
    frame: NDArray[np.uint8], map1: NDArray[np.int16], map2: NDArray[np.uint16]
) -> NDArray[np.uint8]:
    return cast(NDArray[np.uint8], cv2.remap(frame, map1, map2, cv2.INTER_LINEAR))


def get_map1_and_map2(
    camera_matrix: NDArray[np.float64],
    dist_coeff: NDArray[np.float64],
    width: int,
    height: int,
) -> tuple[NDArray[np.int16], NDArray[np.uint16], NDArray[np.float64]]:
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

    return (
        cast(NDArray[np.int16], map1),
        cast(NDArray[np.uint16], map2),
        cast(NDArray[np.float64], new_camera_matrix),
    )

def convert_to_wpi_position(t: NDArray[np.float64]) -> Vector3:
    return Vector3(
        x=float(t[2][0]),
        y=float(-t[0][0]),
        z=float(t[1][0]),
    )

def convert_to_wpi_rotation(R: NDArray[np.float64]) -> Rotation3d:
    return Rotation3d(
        directionX=Vector3(
            x=R[2, 0],
            y=-R[0, 0],
            z=R[1, 0],
        ),
        directionY=Vector3(
            x=R[2, 1],
            y=-R[0, 1],
            z=R[1, 1],
        ),
        directionZ=Vector3(
            x=R[2, 2],
            y=-R[0, 2],
            z=R[1, 2],
        ),
        yaw=float(np.atan2(R[2, 0], R[2, 2])),
    )

def solve_pnp_tag_corners(
    tag_corners: UnprocessedTag,
    tag_size: float,
    camera_matrix: NDArray[np.float64],
    dist_coeff: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
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
    return cast(NDArray[np.float64], R), cast(NDArray[np.float64], tvec)


def solve_pnp_tags_iterative(
    tags: list[UnprocessedTag],
    tag_size: float,
    camera_matrix: NDArray[np.float64],
    dist_coeff: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
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

    return cast(NDArray[np.float64], cv2.Rodrigues(rvec)[0]), cast(
        NDArray[np.float64], tvec
    )


def get_camera_capture_device(camera: CameraParameters) -> AbstractCaptureDevice:
    if (
        camera.camera_type == "OV2311"
        or camera.camera_type == CameraType.OV2311
        or camera.camera_type.value == CameraType.OV2311.value
    ):
        return OV2311Camera(
            camera.camera_path,
            camera.width,
            camera.height,
            camera.max_fps,
            get_np_from_matrix(camera.camera_matrix),
            get_np_from_vector(camera.dist_coeff),
            exposure_time=camera.exposure_time,
        )

    raise ValueError(f"Unsupported camera type: {camera.camera_type}")


def build_detector(config: AprilDetectionConfig) -> pyapriltags.Detector:
    return pyapriltags.Detector(
        families=str(config.family),
        nthreads=config.nthreads,
        quad_decimate=config.quad_decimate,
        quad_sigma=config.quad_sigma,
        refine_edges=config.refine_edges,
        decode_sharpening=config.decode_sharpening,
        debug=0,
    )
