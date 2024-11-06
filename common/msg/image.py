from dataclasses import dataclass
import json
import cv2
import numpy as np
from common import logger


@dataclass
class ImageMessage:
    image: np.ndarray
    camera_name: str
    is_gray: bool

    def from_image_to_cv2(self):
        flag = cv2.IMREAD_GRAYSCALE if self.is_gray else cv2.IMREAD_COLOR
        return cv2.imdecode(self.image, flag)

    @classmethod
    def from_cv2(cls, image: np.ndarray, camera_name: str):
        success, encoded_img = cv2.imencode(
            ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90]
        )

        if not success:
            logger.error("Failed to encode image")
            raise ValueError("Failed to encode image")

        return cls(
            image=encoded_img,
            camera_name=camera_name,
            is_gray=image.ndim == 2,
        )

    @classmethod
    def from_json(cls, json_data: str):
        data = json.loads(json_data)
        data["image"] = np.array(data["image"], dtype=np.uint8)
        return cls(**data)

    def to_json(self):
        data = {
            "image": self.image.tolist(),
            "camera_name": self.camera_name,
            "is_gray": self.is_gray,
        }
        return json.dumps(data)


@dataclass
class TransformImageMessage(ImageMessage):
    do_crop: bool
    make_square: bool

    @classmethod
    def from_json(cls, json_data: str):
        data = json.loads(json_data)
        data["image"] = np.array(data["image"], dtype=np.uint8)
        return cls(**data)

    @classmethod
    def from_bytes(cls, bytes_data: bytes):
        return cls.from_json(bytes_data.decode("utf-8"))

    def to_json(self):
        data = {
            "image": self.image.tolist(),
            "camera_name": self.camera_name,
            "is_gray": self.is_gray,
            "do_crop": self.do_crop,
            "make_square": self.make_square,
        }
        return json.dumps(data)
