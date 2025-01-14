from __future__ import annotations
from enum import Enum

from pydantic import BaseModel


class CalibrationType(Enum):
    CHECKERBOARD = "checkerboard"
    APRILTAG = "apriltag"


class UpdateCalibrationParams(BaseModel):
    checkerboard_width: int
    checkerboard_height: int
    checkerboard_square_size: float
    which_calibration: CalibrationType


class RemoveImage(BaseModel):
    image_id: int
