import toml

from std.config.camera_feed_cleaner import CameraFeedCleanerConfig
from std.config_util import check_config
from std.logger import LogLevel
from std.config.autobahn import AutobahnConfig
from std.config.image_recognition import ImageRecognitionConfig
from std.config.april_detection import AprilDetectionConfig

main_config_required_keys = ["log-level", "measure-speed"]


class Config:
    def __init__(self, config_path: str):
        self.config = toml.load(config_path)

        check_config(self.config, main_config_required_keys, "Main Config")

        self.log_level = LogLevel(self.config["log-level"])
        self.measure_speed = self.config["measure-speed"]

        self.autobahn = AutobahnConfig(self.config["autobahn"])
        self.image_recognition = ImageRecognitionConfig(
            self.config["image-recognition"]
        )
        self.april_detection = AprilDetectionConfig(self.config["april-detection"])
        self.camera_feed_cleaner = CameraFeedCleanerConfig(
            self.config["camera-feed-cleaner"]
        )
