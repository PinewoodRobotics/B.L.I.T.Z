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

from generated.AprilTag_pb2 import AprilTags, Tag


def to_float_list(arr: np.ndarray) -> list:
    return list(arr.flatten()) if arr is not None else []


def to_float(val) -> float:
    if isinstance(val, np.ndarray):
        return float(val.item())
    return float(val) if val is not None else 0.0


def from_detection_to_proto(detection: pyapriltags.Detection) -> Tag:
    if detection.pose_t is None:
        raise ValueError("Detection has no pose data")

    distance_to_camera = float(np.linalg.norm(detection.pose_t))

    x, y, z = detection.pose_t[0], detection.pose_t[1], detection.pose_t[2]

    angle_relative_to_camera_yaw = float(np.arctan2(x, z))
    angle_relative_to_camera_pitch = float(np.arctan2(y, z))

    position_x_relative = float(x)
    position_y_relative = float(y)
    position_z_relative = float(z)

    return Tag(
        tag_family=str(detection.tag_family),
        tag_id=detection.tag_id,
        hamming=detection.hamming,
        decision_margin=detection.decision_margin,
        homography=to_float_list(detection.homography),
        center=to_float_list(detection.center),
        corners=to_float_list(detection.corners),
        pose_R=to_float_list(detection.pose_R) if detection.pose_R is not None else [],
        pose_t=to_float_list(detection.pose_t),
        pose_err=detection.pose_err,
        tag_size=detection.tag_size,
        distance_to_camera=distance_to_camera,
        angle_relative_to_camera_yaw=angle_relative_to_camera_yaw,
        angle_relative_to_camera_pitch=angle_relative_to_camera_pitch,
        position_x_relative=position_x_relative,
        position_y_relative=position_y_relative,
        position_z_relative=position_z_relative,
    )


def process_image(
    image: np.ndarray,
    camera_matrix: np.ndarray,
    detector: pyapriltags.Detector,
    tag_size: float,
    camera_name: str,
):
    fx, fy, cx, cy = (
        camera_matrix[0, 0],
        camera_matrix[1, 1],
        camera_matrix[0, 2],
        camera_matrix[1, 2],
    )

    output = AprilTags(
        camera_name=camera_name,
        image_id=random.randint(0, 1000000),
        tags=[
            from_detection_to_proto(tag)
            for tag in detector.detect(
                image,
                estimate_tag_pose=True,
                camera_params=((fx, fy, cx, cy)),
                tag_size=tag_size,
            )
        ],
        timestamp=int(time.time() * 1000),
    )

    return output


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
