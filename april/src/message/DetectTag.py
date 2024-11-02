from dataclasses import dataclass, field
import json
from typing import List, Optional
import cv2
import numpy as np
import base64

from pyapriltags import Detection


@dataclass
class DetectImage:
    image_encoded_base64: str
    is_grayscale: bool
    camera_name: str

    def decode_image(self):
        image_data = base64.b64decode(self.image_encoded_base64)
        image_np = np.frombuffer(image_data, np.uint8)
        return cv2.imdecode(
            image_np, cv2.IMREAD_GRAYSCALE if self.is_grayscale else cv2.IMREAD_COLOR
        )

    @classmethod
    def from_json(cls, json_data):
        data = json.loads(json_data)
        return cls(**data)


@dataclass
class PositionData:
    distance_to_camera: float
    angle_relative_to_camera_yaw: float
    angle_relative_to_camera_pitch: float
    position_x_relative: float
    position_y_relative: float

    def __init__(self, raw_detection_data: "Detection"):
        tvec = raw_detection_data.pose_t
        self.distance_to_camera = float(np.linalg.norm(tvec))

        rvec = raw_detection_data.pose_R
        yaw = np.arctan2(rvec[2, 0], rvec[0, 0])
        pitch = np.arctan2(rvec[1, 0], np.sqrt(rvec[0, 0] ** 2 + rvec[2, 0] ** 2))
        self.angle_relative_to_camera_yaw = float(yaw)
        self.angle_relative_to_camera_pitch = float(pitch)

        self.position_x_relative = float(tvec[0, 0])
        self.position_y_relative = float(tvec[1, 0])

    def to_dict(self):
        return {
            "distance_to_camera": self.distance_to_camera,
            "angle_relative_to_camera_yaw": self.angle_relative_to_camera_yaw,
            "angle_relative_to_camera_pitch": self.angle_relative_to_camera_pitch,
            "position_x_relative": self.position_x_relative,
            "position_y_relative": self.position_y_relative,
        }


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

    def to_dict(self):
        # Ensure tag_family is a string, not bytes
        tag_family_str = (
            self.tag_family.decode("utf-8")
            if isinstance(self.tag_family, bytes)
            else self.tag_family
        )

        return {
            "tag_family": tag_family_str,
            "tag_id": self.tag_id,
            "hamming": self.hamming,
            "decision_margin": self.decision_margin,
            "homography": self.homography,
            "center": self.center,
            "corners": self.corners,
            "pose_R": (
                self.pose_R if self.pose_R is None else np.array(self.pose_R).tolist()
            ),
            "pose_t": (
                self.pose_t if self.pose_t is None else np.array(self.pose_t).tolist()
            ),
            "pose_err": self.pose_err,
            "tag_size": self.tag_size,
        }


@dataclass
class Tag:
    raw_detection_data: NamedDetection
    camera_position_data: PositionData

    def to_dict(self):
        return {
            "raw_detection_data": self.raw_detection_data.to_dict(),
            "camera_position_data": self.camera_position_data.to_dict(),
        }

    def to_json(self):
        return json.dumps(self.to_dict())


class PostOutput:
    def __init__(self, camera_name, tags: list[Tag]):
        self.camera_name = camera_name
        self.tags = tags

    def to_dict(self):
        return {
            "camera_name": self.camera_name,
            "tags": [tag.to_dict() for tag in self.tags],
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    def add_tag(self, tag: "Tag"):
        self.tags.append(tag)
