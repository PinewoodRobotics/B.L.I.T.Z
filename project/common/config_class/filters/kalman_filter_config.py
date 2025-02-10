from pydantic import BaseModel
from typing import Any, Dict
from enum import Enum


class MeasurementType(Enum):
    APRIL_TAG = "april-tag"
    ODOMETRY = "odometry"
    IMU = "imu"


class KalmanFilterSensorConfig(BaseModel):
    measurement_noise_matrix: list[list[float]]
    measurement_conversion_matrix: list[list[float]]


class KalmanFilterConfig(BaseModel):
    state_vector: list[float]
    time_step: float
    state_transition_matrix: list[list[float]]
    uncertainty_matrix: list[list[float]]
    process_noise_matrix: list[list[float]]
    dim_x_z: list[int]
    sensors: dict[str, dict[str, Any]]
    sensors_config: dict[MeasurementType, KalmanFilterSensorConfig] = {}

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(**config)
        self.sensors_config = {}
        for sensor, sensor_config in self.sensors.items():
            sensor_enum = MeasurementType(sensor)
            self.sensors_config[sensor_enum] = KalmanFilterSensorConfig(**sensor_config)
