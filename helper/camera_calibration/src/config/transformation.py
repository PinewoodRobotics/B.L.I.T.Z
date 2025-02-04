from typing import TYPE_CHECKING

import cv2
import numpy as np
from pydantic import BaseModel

if TYPE_CHECKING:
    from schema.update_config import UpdateConfig


class Range(BaseModel):
    min: float
    max: float


class CameraCalibration(BaseModel):
    undistort: bool
    camera_matrix: list[list[float]]
    dist_coeff: list[float]


class Threshholding(BaseModel):
    hue: Range
    saturation: Range
    value: Range

    def apply(self, image: np.ndarray):
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hsv_image[:, :, 0] = np.clip(hsv_image[:, :, 0], self.hue.min, self.hue.max)
        hsv_image[:, :, 1] = np.clip(
            hsv_image[:, :, 1], self.saturation.min, self.saturation.max
        )
        hsv_image[:, :, 2] = np.clip(hsv_image[:, :, 2], self.value.min, self.value.max)

        return cv2.cvtColor(hsv_image, cv2.COLOR_HSV2BGR)


class CameraSettings(BaseModel):
    exposure: Range
    gain: Range
    gamma: Range

    def apply(self, camera: cv2.VideoCapture) -> cv2.VideoCapture:
        camera.set(cv2.CAP_PROP_EXPOSURE, (self.exposure.min + self.exposure.max) / 2)
        camera.set(cv2.CAP_PROP_GAIN, (self.gain.min + self.gain.max) / 2)
        camera.set(cv2.CAP_PROP_GAMMA, (self.gamma.min + self.gamma.max) / 2)
        return camera


class Filtering(BaseModel):
    object_size: Range
    bounding_box_aspect_ratio: Range
    fullness: Range  # IDK what this is lmao

    def apply(self, image: np.ndarray):
        pass


class QuadDetection(BaseModel):
    quad_decimate: float = 2.0
    quad_sigma: float = 0.0
    refine_edges: int = 1
    decode_sharpening: float = 0.25
    tag_size_m: float = 0.01


class TransformationConfig(BaseModel):
    detect_april_tags: bool
    use_grayscale: bool
    undistort: CameraCalibration
    camera_settings: CameraSettings
    threshholding: Threshholding
    filtering: Filtering
    april_tag_config: QuadDetection

    def update_config(self, new_config: "UpdateConfig"):
        if new_config.detect_april_tags is not None:
            self.detect_april_tags = new_config.detect_april_tags
        if new_config.undistort is not None:
            self.undistort = new_config.undistort
        if new_config.use_grayscale is not None:
            self.use_grayscale = new_config.use_grayscale
        if new_config.camera_settings:
            if new_config.camera_settings.exposure:
                self.camera_settings.exposure = new_config.camera_settings.exposure
            if new_config.camera_settings.gain:
                self.camera_settings.gain = new_config.camera_settings.gain
            if new_config.camera_settings.gamma:
                self.camera_settings.gamma = new_config.camera_settings.gamma
        if new_config.threshholding:
            if new_config.threshholding.hue:
                self.threshholding.hue = new_config.threshholding.hue
            if new_config.threshholding.saturation:
                self.threshholding.saturation = new_config.threshholding.saturation
            if new_config.threshholding.value:
                self.threshholding.value = new_config.threshholding.value
        if new_config.filtering:
            self.filtering.object_size = new_config.filtering.object_size
            if new_config.filtering.bounding_box_aspect_ratio:
                self.filtering.bounding_box_aspect_ratio = (
                    new_config.filtering.bounding_box_aspect_ratio
                )
            if new_config.filtering.fullness:
                self.filtering.fullness = new_config.filtering.fullness
