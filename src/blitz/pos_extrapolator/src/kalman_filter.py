from filterpy.kalman import KalmanFilter
import numpy as np

from blitz.generated.thrift.config.kalman_filter.ttypes import (
    KalmanFilterConfig,
    KalmanFilterSensorConfig,
)


class KalmanFilterStrategy:
    def __init__(self, config: KalmanFilterConfig):
        self.kf = KalmanFilter(dim_x=config.dim_x_z[0], dim_z=config.dim_x_z[1])
        self.kf.x = np.array(config.state_vector)
        self.kf.P = np.array(config.uncertainty_matrix)
        self.kf.Q = np.array(config.process_noise_matrix)
        self.kf.H = np.array(config.state_transition_matrix)
        self.sensors = config.sensors

    def get_sensor_config(self, data_type: MeasurementType) -> KalmanFilterSensorConfig:
        return self.sensors[data_type]

    def insert_data(
        self, data: list[float], data_type: MeasurementType, noise: float
    ) -> None:
        z = np.array(data)

        # Ensure theta difference (index 4) is wrapped to [-π, π]
        if len(z) > 4:  # Only apply if theta is present
            theta_residual = z[4] - self.kf.x[4]
            z[4] = self.kf.x[4] + np.arctan2(
                np.sin(theta_residual), np.cos(theta_residual)
            )

        self.kf.update(
            z,
            np.array(self.sensors[data_type].measurement_noise_matrix) * noise,
            np.array(self.sensors[data_type].measurement_conversion_matrix),
        )

    def predict(self):
        self.kf.predict()
        self.kf.x[4] = np.arctan2(np.sin(self.kf.x[4]), np.cos(self.kf.x[4]))

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
        return np.linalg.det(self.kf.P[2:4, 2:4])

    def get_rotation_confidence(self) -> float:
        return self.kf.P[4, 4]

    def get_confidence(self) -> float:
        return (
            self.get_position_confidence()
            + self.get_velocity_confidence()
            + self.get_rotation_confidence()
        )

    def get_filtered_data(self) -> list[float]:
        return self.kf.x.tolist()

    def update_transformation_delta_t(self, new_delta_t: float):
        self.kf.F[0][2] = new_delta_t
        self.kf.F[1][3] = new_delta_t
