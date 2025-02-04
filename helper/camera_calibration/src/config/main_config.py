from pydantic import BaseModel

from config.camera import CameraConfig
from config.calibration import (
    CalibrationConfig,
)
from config.transformation import TransformationConfig


class MainBackendConfig:
    def __init__(self, dict):
        self.stream_hosting_port = dict["stream_hosting_port"]
        self.main_hosting_port = dict["main_hosting_port"]


class MainAppConfig(BaseModel):
    camera: CameraConfig
    transformation: TransformationConfig
    calibration: CalibrationConfig

    def save(self, path: str):
        with open(path, "w") as f:
            f.write(self.model_dump_json())
