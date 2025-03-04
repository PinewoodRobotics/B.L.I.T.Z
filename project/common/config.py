import subprocess
import json
from pydantic import BaseModel

from project.common.config_class.camera_parameters import (
    CameraParameters,
)
from project.common.config_class.pos_extrapolator import PosExtrapolatorConfig
from project.common.config_class.profiler import LoggerConfig
from project.common.config_class.autobahn import AutobahnConfig
from project.common.config_class.image_recognition import ImageRecognitionConfig
from project.common.config_class.april_detection import AprilDetectionConfig


class Config(BaseModel):
    autobahn: AutobahnConfig
    pos_extrapolator: PosExtrapolatorConfig
    image_recognition: ImageRecognitionConfig
    cameras: list[CameraParameters]
    april_detection: AprilDetectionConfig
    logger: LoggerConfig

    @classmethod
    def load_config(cls, config_path: str = "config/") -> "Config":
        try:
            result = subprocess.run(
                ["npx", "tsx", config_path], capture_output=True, text=True, check=True
            )
            config_json = result.stdout
            return Config.model_validate_json(config_json)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to run 'tsc config/': {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON output from tsc: {e}")

    @classmethod
    def from_json(cls, file_path: str) -> "Config":
        with open(file_path, "r") as f:
            config_json = f.read()

        return Config.model_validate_json(config_json)

    @classmethod
    def from_uncertainty_config(cls, file_path: str | None = None) -> "Config":
        if file_path is None:
            return cls.load_config()

        return cls.from_json(file_path)
