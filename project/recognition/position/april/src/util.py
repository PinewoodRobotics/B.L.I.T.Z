import numpy as np
import pyapriltags

from generated.AprilTag_pb2 import Tag


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
