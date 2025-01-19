from enum import Enum
import toml

from project.common.config_class.camera_parameters import CameraParametersConfig
from project.common.config_class.config_template import ConfigTemplate
from project.common.config_class.filters.kalman_filter_config import KalmanFilterConfig
from project.common.config_class.filters.weighted_avg_config import WeightedAvgConfig
from project.common.config_class.pos_extrapolator import PosExtrapolatorConfig
from project.common.debug import logger
from project.common.config_class.profiler import ProfilerConfig
from project.common.error.missing_key_error import MissingKeyError
from project.common.debug.logger import LogLevel
from project.common.config_class.autobahn import AutobahnConfig
from project.common.config_class.image_recognition import ImageRecognitionConfig
from project.common.config_class.april_detection import AprilDetectionConfig


class Module(Enum):
    AUTOBAHN = "autobahn"
    IMAGE_RECOGNITION = "image-recognition"
    APRIL_DETECTION = "april-detection"
    PROFILER = "profiler"
    CAMERA_PARAMETERS = "camera-parameters"
    POS_EXTRAPOLATOR = "pos-extrapolator"
    KALMAN_FILTER = "kalman-filter"
    WEIGHTED_AVG_FILTER = "weighted-average-filter"


main_config_required_keys = ["log-level", "measure-speed"]


class Config(ConfigTemplate):
    def __init__(self, config_path: str, exclude: list[Module] = []):
        self.__config_raw = toml.load(config_path)
        self.__config_path = config_path
        self.__load(self.__config_raw, exclude)

    def __load(self, config_raw: dict, exclude: list[Module] = []):
        self.check_config(config_raw, main_config_required_keys, "Main Config")

        self.log_level = LogLevel(config_raw["log-level"])
        self.measure_speed = config_raw["measure-speed"]

        if Module.AUTOBAHN not in exclude:
            self.autobahn = AutobahnConfig(config_raw["autobahn"])

        if Module.IMAGE_RECOGNITION not in exclude:
            self.image_recognition = ImageRecognitionConfig(
                config_raw["image-recognition"]
            )

        if Module.CAMERA_PARAMETERS not in exclude:
            self.camera_parameters = CameraParametersConfig(
                config_raw["camera-parameters"]
            )

        if Module.POS_EXTRAPOLATOR not in exclude:
            self.pos_extrapolator = PosExtrapolatorConfig(
                config_raw["pos-extrapolator"]
            )

        if Module.KALMAN_FILTER not in exclude:
            self.kalman_filter = KalmanFilterConfig(config_raw["kalman-filter"])

        if Module.WEIGHTED_AVG_FILTER not in exclude:
            self.weighted_avg_filter = WeightedAvgConfig(
                config_raw["weighted-average-filter"]
            )

        if Module.APRIL_DETECTION not in exclude:
            self.april_detection = AprilDetectionConfig(config_raw["april-detection"])

        if Module.PROFILER not in exclude:
            self.profiler = ProfilerConfig(config_raw["profiler"])

    def reload(self):
        logger.info("Reloading config...")
        self.__config_raw = toml.load(self.__config_path)
        self.__load(self.__config_raw)
