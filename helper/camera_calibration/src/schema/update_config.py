from __future__ import annotations

from typing import Optional
from pydantic import BaseModel

from config.transformation import (
    CameraCalibration,
    CameraSettings,
    Filtering,
    QuadDetection,
    Threshholding,
)


class UpdateConfig(BaseModel):
    detect_april_tags: Optional[bool] = None
    use_grayscale: Optional[bool] = None
    undistort: Optional[CameraCalibration] = None
    camera_settings: Optional[CameraSettings] = None
    threshholding: Optional[Threshholding] = None
    filtering: Optional[Filtering] = None
    april_tag_config: Optional[QuadDetection] = None
