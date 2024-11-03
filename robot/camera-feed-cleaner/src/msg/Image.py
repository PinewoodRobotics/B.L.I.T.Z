import base64
from dataclasses import dataclass
import json

import cv2
import numpy as np


@dataclass
class Image:
    image_encoded_base64: str
    camera_name: str
    do_cropping: bool

    def decode_image(self):
        image_data = base64.b64decode(self.image_encoded_base64)
        image_np = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        return image

    @classmethod
    def from_json(cls, json_data):
        data = json.loads(json_data)
        return cls(**data)


@dataclass
class ImageOutput:
    image_encoded_base64: str
    camera_name: str

    def to_json(self):
        return json.dumps(self.__dict__)
