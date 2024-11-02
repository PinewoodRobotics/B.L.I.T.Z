from dataclasses import dataclass, field
import json
import cv2
import numpy as np
import base64

from pyapriltags import Detection


@dataclass
class DetectImage:
    image_encoded_base64: str
    is_grayscale: bool
    camera: str

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

    def __init__(self, raw_detection_data: Detection):
        tvec = raw_detection_data.pose_t
        self.distance_to_camera = np.linalg.norm(tvec)

        rvec = raw_detection_data.pose_R
        yaw = np.arctan2(rvec[2, 0], rvec[0, 0])
        pitch = np.arctan2(rvec[1, 0], np.sqrt(rvec[0, 0] ** 2 + rvec[2, 0] ** 2))
        self.angle_relative_to_camera_yaw = yaw
        self.angle_relative_to_camera_pitch = pitch

        self.position_x_relative = tvec[0, 0]
        self.position_y_relative = tvec[1, 0]


@dataclass
class Tag:
    raw_detection_data: Detection
    camera_position_data: PositionData

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)


class PostOutput:
    def __init__(self, camera_name, tags):
        self.camera_name = camera_name
        self.tags = tags

    def to_json(self):
        # Use a custom serializer to handle non-serializable types
        return json.dumps(self, default=self._serialize)

    def _serialize(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, bytes):
            return obj.decode("utf-8")
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)

    def add_tag(self, tag: "Tag"):
        self.tags.append(tag)
