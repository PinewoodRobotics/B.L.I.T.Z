from filterpy.kalman import KalmanFilter
import numpy as np
from project.common.config_class.filters.kalman_filter_config import (
    KalmanFilterConfig,
    MeasurementType,
)
from project.recognition.position.pos_extrapolator.src.filter import FilterStrategy


class KalmanFilterStrategy(FilterStrategy):
    """
    Basic kalman filter. Essentially you input a bunch of data and it outputs a kalman filtered position.
    Note: this is much more accurate than the other filters (probably).
    """

    def __init__(self, config: KalmanFilterConfig):
        super().__init__(config)
        self.kf = KalmanFilter(dim_x=config.dim_x_z[0], dim_z=config.dim_x_z[1])
        self.kf.x = np.array(config.state_vector)
        self.kf.P = np.array(config.uncertainty_matrix)
        self.kf.Q = np.array(config.process_noise_matrix)
        self.kf.H = np.array(config.state_transition_matrix)
        self.sensors = config.sensors_config

    def filter_data(self, data: list[float], data_type: MeasurementType) -> None:
        self.kf.update(
            data,
            self.sensors[data_type].measurement_noise_matrix,
            self.sensors[data_type].measurement_conversion_matrix,
        )

    def predict(self):
        self.kf.predict()

    def get_state(self) -> list[float]:
        return self.kf.x.tolist()

    def get_position_confidence(self) -> float:
        P_position = self.kf.P[:2, :2]

        determinant = np.linalg.det(P_position)

        # Optionally, you could also compute trace or ellipse radius
        # trace = np.trace(P_position)
        # eigenvalues, _ = np.linalg.eig(P_position)
        # ellipse_radius = np.sqrt(np.max(eigenvalues))

        return determinant

    def get_velocity_confidence(self) -> float:
        P_velocity = self.kf.P[2:4, 2:4]

        determinant = np.linalg.det(P_velocity)

        return determinant

    def get_rotation_confidence(self) -> float:
        P_theta = self.kf.P[4, 4]

        return P_theta

    def get_confidence(self) -> float:
        return (
            self.get_position_confidence()
            + self.get_velocity_confidence()
            + self.get_rotation_confidence()
        )

    def get_filtered_data(self) -> list[float]:
        return self.kf.x.tolist()
