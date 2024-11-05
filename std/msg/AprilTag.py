from dataclasses import dataclass
from typing import List, Optional
from pyapriltags import Detection

import numpy as np

from std.json_util import to_json


@dataclass
class NamedDetection:
    tag_family: str
    tag_id: int
    hamming: int
    decision_margin: float
    homography: List[float]
    center: List[float]
    corners: List[List[float]]
    pose_R: Optional[List[List[float]]]
    pose_t: Optional[List[float]]
    pose_err: Optional[float]
    tag_size: Optional[float]

    @staticmethod
    def from_raw(raw_detection: Detection) -> "NamedDetection":
        return NamedDetection(
            tag_family=raw_detection.tag_family.decode("utf-8"),
            tag_id=raw_detection.tag_id,
            hamming=raw_detection.hamming,
            decision_margin=raw_detection.decision_margin,
            homography=raw_detection.homography.tolist(),
            center=raw_detection.center.tolist(),
            corners=raw_detection.corners.tolist(),
            pose_R=raw_detection.pose_R.tolist() if raw_detection.pose_R else None,
            pose_t=raw_detection.pose_t.tolist() if raw_detection.pose_t else None,
            pose_err=raw_detection.pose_err,
            tag_size=raw_detection.tag_size,
        )

    def to_json(self):
        return to_json(self)


class AprilPositionData:
    distance_to_camera: float
    angle_relative_to_camera_yaw: float
    angle_relative_to_camera_pitch: float
    position_x_relative: float
    position_y_relative: float
    position_z_relative: float

    def __init__(self, raw_detection_data: NamedDetection):
        if raw_detection_data.pose_t is None:
            raise ValueError("pose_t is None, cannot calculate position data")

        pose_t = np.array(raw_detection_data.pose_t)
        self.distance_to_camera = float(np.linalg.norm(pose_t))

        x, y, z = pose_t[0], pose_t[1], pose_t[2]

        self.angle_relative_to_camera_yaw = np.arctan2(x, z)
        self.angle_relative_to_camera_pitch = np.arctan2(y, z)

        self.position_x_relative = float(x)
        self.position_y_relative = float(y)
        self.position_z_relative = float(z)

    def to_json(self):
        return to_json(self)


@dataclass
class Tag:
    raw_detection_data: NamedDetection
    camera_position_data: AprilPositionData

    @staticmethod
    def from_raw(raw_detection: Detection) -> "Tag":
        named_detection = NamedDetection.from_raw(raw_detection)
        return Tag(
            raw_detection_data=named_detection,
            camera_position_data=AprilPositionData(named_detection),
        )

    def to_json(self):
        return to_json(self)


class AprilTags(List[Tag]):
    camera_name: str

    def to_json(self):
        return to_json(self)
