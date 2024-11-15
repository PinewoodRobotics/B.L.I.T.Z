from enum import Enum
import toml

from common import logger
from common.config_class.profiler import ProfilerConfig
from common.config_util import check_config
from common.logger import LogLevel
from common.config_class.autobahn import AutobahnConfig
from common.config_class.image_recognition import ImageRecognitionConfig
from common.config_class.april_detection import AprilDetectionConfig
from common.config_class.camera_feed_cleaner import CameraFeedCleanerConfig


class Module(Enum):
    AUTOBAHN = "autobahn"
    IMAGE_RECOGNITION = "image-recognition"
    APRIL_DETECTION = "april-detection"
    CAMERA_FEED_CLEANER = "camera-feed-cleaner"
    PROFILER = "profiler"


main_config_required_keys = ["log-level", "measure-speed"]


class Config:
    def __init__(self, config_path: str, exclude: list[Module] = []):
        self.__config_raw = toml.load(config_path)
        self.__config_path = config_path
        self.__load(self.__config_raw, exclude)

    def __load(self, config_raw: dict, exclude: list[Module] = []):
        check_config(config_raw, main_config_required_keys, "Main Config")

        self.log_level = LogLevel(config_raw["log-level"])
        self.measure_speed = config_raw["measure-speed"]

        if Module.AUTOBAHN not in exclude:
            self.autobahn = AutobahnConfig(config_raw["autobahn"])

        if Module.IMAGE_RECOGNITION not in exclude:
            self.image_recognition = ImageRecognitionConfig(
                config_raw["image-recognition"]
            )

        if Module.APRIL_DETECTION not in exclude:
            self.april_detection = AprilDetectionConfig(config_raw["april-detection"])

        if Module.CAMERA_FEED_CLEANER not in exclude:
            self.camera_feed_cleaner = CameraFeedCleanerConfig(
                config_raw["camera-feed-cleaner"]
            )

        if Module.PROFILER not in exclude:
            self.profiler = ProfilerConfig(config_raw["profiler"])

    def reload(self):
        logger.info("Reloading config...")
        self.__config_raw = toml.load(self.__config_path)
        self.__load(self.__config_raw)
