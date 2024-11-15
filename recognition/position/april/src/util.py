import numpy as np
import pyapriltags

from common.config import Config
from generated.common.proto.AprilTag_pb2 import Tag


class DetectionPosition:
    distance_to_camera: float
    angle_relative_to_camera_yaw: float
    angle_relative_to_camera_pitch: float
    position_x_relative: float
    position_y_relative: float
    position_z_relative: float

    def __init__(
        self,
        pose_t: np.ndarray,
    ):
        self.distance_to_camera = float(np.linalg.norm(pose_t))

        x, y, z = pose_t[0], pose_t[1], pose_t[2]

        self.angle_relative_to_camera_yaw = np.arctan2(x, z)
        self.angle_relative_to_camera_pitch = np.arctan2(y, z)

        self.position_x_relative = float(x)
        self.position_y_relative = float(y)
        self.position_z_relative = float(z)


def from_detection_to_proto(detection: pyapriltags.Detection) -> Tag:
    detection_position = crunch_numbers(detection)
    return Tag(
        tag_family=str(detection.tag_family),
        tag_id=detection.tag_id,
        hamming=detection.hamming,
        decision_margin=detection.decision_margin,
        homography=detection.homography,
        center=detection.center,
        corners=detection.corners,
        pose_R=detection.pose_R,
        pose_t=detection.pose_t,
        pose_err=detection.pose_err,
        tag_size=detection.tag_size,
        distance_to_camera=detection_position.distance_to_camera,
        angle_relative_to_camera_yaw=detection_position.angle_relative_to_camera_yaw,
        angle_relative_to_camera_pitch=detection_position.angle_relative_to_camera_pitch,
        position_x_relative=detection_position.position_x_relative,
        position_y_relative=detection_position.position_y_relative,
        position_z_relative=detection_position.position_z_relative,
    )


def crunch_numbers(detection: pyapriltags.Detection) -> DetectionPosition:
    if detection.pose_t is None:
        raise ValueError("Detection has no pose data")
    return DetectionPosition(pose_t=detection.pose_t)
