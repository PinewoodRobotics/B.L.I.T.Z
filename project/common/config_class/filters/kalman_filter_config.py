from enum import Enum
from typing import Any, Dict
from project.common.config_class.config_template import ConfigTemplate

required_keys = [
    "state-vector",
    "time-step",
    "state-transition-matrix",
    "uncertainty-matrix",
    "process-noise-matrix",
    "dim-x-z",
    "sensors",
]

required_keys_sensor = [
    "measurement-noise-matrix",
    "measurement-conversion-matrix",
]


class MeasurementType(Enum):
    APRIL_TAG = "april-tag"
    ODOMETRY = "odometry"
    CAMERA = "camera"


class KalmanFilterConfig(ConfigTemplate):
    def __init__(self, config: Dict[str, Any]) -> None:
        self.check_config(config, required_keys, "KalmanFilterConfig")
        self.state_vector: list[float] = config["state-vector"]
        self.time_step: float = config["time-step"]
        self.state_transition_matrix: list[list[float]] = config[
            "state-transition-matrix"
        ]
        self.uncertainty_matrix: list[list[float]] = config["uncertainty-matrix"]
        self.process_noise_matrix: list[list[float]] = config["process-noise-matrix"]
        self.dim_x_z: list[int] = config["dim-x-z"]
        self.sensors_used = config["sensors"]
        self.sensors_config: dict[MeasurementType, KalmanFilterSensorConfig] = {}
        for sensor in self.sensors_used:
            sensor_enum = MeasurementType(sensor)
            self.sensors_config[sensor_enum] = KalmanFilterSensorConfig(config[sensor])


class KalmanFilterSensorConfig(ConfigTemplate):
    def __init__(self, config: Dict[str, Any]) -> None:
        self.check_config(config, required_keys_sensor, "KalmanFilterSensorConfig")
        self.measurement_noise_matrix = config["measurement-noise-matrix"]
        self.measurement_conversion_matrix = config["measurement-conversion-matrix"]
