from typing import Any, Dict
from project.common.config_class.config_template import ConfigTemplate
from project.common.config_class.filters.kalman_filter_config import MeasurementType

required_keys = ["sensors"]
required_keys_sensor = ["weight"]


class WeightedAvgConfig(ConfigTemplate):
    def __init__(self, config: Dict[str, Any]) -> None:
        self.check_config(config, required_keys, "WeightedAvgConfig")
        self.sensors = config["sensors"]
        self.sensors_config: dict[MeasurementType, SensorConfig] = {}
        for sensor in self.sensors:
            self.sensors_config[sensor] = SensorConfig(config[sensor])


class SensorConfig(ConfigTemplate):
    def __init__(self, config: Dict[str, Any]) -> None:
        self.check_config(config, required_keys_sensor, "SensorConfig")
        self.weight = config["weight"]
