from dataclasses import dataclass
import json

import cv2
import numpy as np

from std.json_util import to_json


@dataclass
class ImageMessage:
    image: bytes
    camera_name: str
    is_gray: bool

    def from_image_to_cv2(self):
        return cv2.imdecode(np.frombuffer(self.image, np.uint8), cv2.IMREAD_COLOR)

    @classmethod
    def from_json(cls, json_data: str):
        data = json.loads(json_data)
        return cls(**data)

    def to_json(self):
        return to_json(self)


@dataclass
class TransformImageMessage(ImageMessage):
    do_crop: bool
    make_square: bool

    @classmethod
    def from_json(cls, json_data: str):
        data = json.loads(json_data)
        return cls(**data)

    def to_json(self):
        return to_json(self)
