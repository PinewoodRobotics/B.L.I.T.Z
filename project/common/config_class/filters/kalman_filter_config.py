from pydantic import BaseModel
from enum import Enum


class MeasurementType(Enum):
    APRIL_TAG = "april-tag"
    ODOMETRY = "odometry"
    IMU = "imu"


class KalmanFilterSensorConfig(BaseModel):
    measurement_noise_matrix: list[list[float]]
    measurement_conversion_matrix: list[list[float]]
    name: str


class KalmanFilterConfig(BaseModel):
    state_vector: list[float]
    state_transition_matrix: list[list[float]]
    uncertainty_matrix: list[list[float]]
    process_noise_matrix: list[list[float]]
    time_step_initial: float
    dim_x_z: list[int]
    sensors: dict[MeasurementType, list[KalmanFilterSensorConfig]] = {}
