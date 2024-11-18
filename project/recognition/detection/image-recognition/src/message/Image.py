import base64
from dataclasses import dataclass
import json

import cv2
import numpy as np
import torch


@dataclass
class DetectImage:
    image_encoded_base64: str

    def decode_image(self):
        image_data = base64.b64decode(self.image_encoded_base64)
        image_np = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(image_np, cv2.COLOR_BGR2RGB)
        return image

    @classmethod
    def from_json(cls, json_data):
        data = json.loads(json_data)
        return cls(**data)


class Box:

    def __init__(self, label: str, score: float, bounding_box: list[float, float]):
        self.label = label
        self.score = score
        self.bounding_box = bounding_box

    def to_dict(self):
        return {
            "label": self.label,
            "score": self.score,
            "bounding_box": self.bounding_box,
        }


class ImageRecognitionOutput:
    boxes: list[Box]

    def __init__(self, boxes: list[Box]):
        self.boxes = boxes

    def add_box(self, box: Box):
        self.boxes.append(box)

    def to_dict(self):
        return {
            "boxes": [box.to_dict() for box in self.boxes],
        }

    def to_json(self):
        return json.dumps(self.to_dict())
