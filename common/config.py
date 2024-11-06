from enum import Enum
import toml

from config_util import check_config
from logger import LogLevel
from config_class.autobahn import AutobahnConfig
from config_class.image_recognition import ImageRecognitionConfig
from config_class.april_detection import AprilDetectionConfig
from config_class.camera_feed_cleaner import CameraFeedCleanerConfig


class Module(Enum):
    AUTOBAHN = "autobahn"
    IMAGE_RECOGNITION = "image-recognition"
    APRIL_DETECTION = "april-detection"
    CAMERA_FEED_CLEANER = "camera-feed-cleaner"


main_config_required_keys = ["log-level", "measure-speed"]


class Config:
    def __init__(self, config_path: str, exclude: list[Module] = []):
        self.__config_raw = toml.load(config_path)
        check_config(self.__config_raw, main_config_required_keys, "Main Config")

        self.log_level = LogLevel(self.__config_raw["log-level"])
        self.measure_speed = self.__config_raw["measure-speed"]

        if Module.AUTOBAHN not in exclude:
            self.autobahn = AutobahnConfig(self.__config_raw["autobahn"])

        if Module.IMAGE_RECOGNITION not in exclude:
            self.image_recognition = ImageRecognitionConfig(
                self.__config_raw["image-recognition"]
            )

        if Module.APRIL_DETECTION not in exclude:
            self.april_detection = AprilDetectionConfig(
                self.__config_raw["april-detection"]
            )

        if Module.CAMERA_FEED_CLEANER not in exclude:
            self.camera_feed_cleaner = CameraFeedCleanerConfig(
                self.__config_raw["camera-feed-cleaner"]
            )
