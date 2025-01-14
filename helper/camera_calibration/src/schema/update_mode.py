from dataclasses import dataclass
from enum import Enum


class Mode(Enum):
    CHECKERBOARD = "checkerboard"
    APRILTAG = "apriltag"
    VIDEO = "video"


@dataclass
class UpdateMode:
    new_mode: Mode
