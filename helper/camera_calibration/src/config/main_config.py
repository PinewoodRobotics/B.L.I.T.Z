from dataclasses import dataclass

from config.camera import CameraConfig
from config.transformation import TransformationConfig


class MainBackendConfig:
    def __init__(self, dict):
        self.port = dict["hosting_port"]


@dataclass
class MainAppConfig:
    camera: CameraConfig
    transformation: TransformationConfig
