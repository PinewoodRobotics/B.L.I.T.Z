import subprocess
import json
from pydantic import BaseModel

from project.common.config_class.camera_parameters import CameraParametersConfig
from project.common.config_class.filters.kalman_filter_config import KalmanFilterConfig
from project.common.config_class.filters.weighted_avg_config import WeightedAvgConfig
from project.common.config_class.pos_extrapolator import PosExtrapolatorConfig
from project.common.config_class.profiler import ProfilerConfig
from project.common.debug.logger import LogLevel
from project.common.config_class.autobahn import AutobahnConfig
from project.common.config_class.image_recognition import ImageRecognitionConfig
from project.common.config_class.april_detection import AprilDetectionConfig


class Config(BaseModel):
    measure_speed: bool
    log_level: LogLevel
    autobahn: AutobahnConfig
    image_recognition: ImageRecognitionConfig
    camera_parameters: CameraParametersConfig
    pos_extrapolator: PosExtrapolatorConfig
    kalman_filter: KalmanFilterConfig
    weighted_avg_filter: WeightedAvgConfig
    april_detection: AprilDetectionConfig
    profiler: ProfilerConfig

    @classmethod
    def load_config(cls) -> "Config":
        try:
            result = subprocess.run(
                ["npx", "tsx", "config/"], capture_output=True, text=True, check=True
            )
            config_json = result.stdout
            return Config.model_validate_json(config_json)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to run 'tsc config/': {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON output from tsc: {e}")
