from filterpy.kalman import ExtendedKalmanFilter
import numpy as np

from blitz.common.util.math import get_np_from_matrix
from blitz.generated.thrift.config.kalman_filter.ttypes import (
    KalmanFilterConfig,
)
from blitz.pos_extrapolator.data_prep import KalmanFilterInput
from blitz.pos_extrapolator.filter_strat import GenericFilterStrategy


class ExtendedKalmanFilterStrategy(ExtendedKalmanFilter, GenericFilterStrategy):
    def __init__(self, config: KalmanFilterConfig, do_wrap_theta: bool = True):
        super().__init__(dim_x=config.dim_x_z[0], dim_z=config.dim_x_z[1])
        self.x = np.array(config.state_vector)
        self.P = np.array(config.uncertainty_matrix)
        self.Q = np.array(config.process_noise_matrix)
        self.H = np.array(config.state_transition_matrix)
        self.do_wrap_theta = do_wrap_theta
        self.config = config

    def insert_data(self, data: KalmanFilterInput) -> None:
        self.predict()
        # self.x[4] = np.arctan2(np.sin(self.x[4]), np.cos(self.x[4]))

        z = np.array(data.input_list)

        # Ensure theta difference (index 4) is wrapped to [-π, π]
        if len(z) > 4 and self.do_wrap_theta:  # Only apply if theta is present
            theta_residual = z[4] - self.x[4]
            z[4] = self.x[4] + np.arctan2(
                np.sin(theta_residual), np.cos(theta_residual)
            )

        self.update(
            z,
            get_np_from_matrix(
                self.config.sensors[data.sensor_type][
                    data.sensor_id
                ].measurement_noise_matrix
            ),
            get_np_from_matrix(
                self.config.sensors[data.sensor_type][
                    data.sensor_id
                ].measurement_conversion_matrix
            ),
        )

    def get_state(self) -> list[float]:
        return [float(x) for x in self.x.flatten()]

    def get_position_confidence(self) -> float:
        P_position = self.P[:2, :2]

        determinant = np.linalg.det(P_position)

        # Optionally, you could also compute trace or ellipse radius
        # trace = np.trace(P_position)
        # eigenvalues, _ = np.linalg.eig(P_position)
        # ellipse_radius = np.sqrt(np.max(eigenvalues))

        return determinant

    def get_velocity_confidence(self) -> float:
        return np.linalg.det(self.P[2:4, 2:4])

    def get_rotation_confidence(self) -> float:
        return self.P[4, 4]

    def get_confidence(self) -> float:
        return (
            self.get_position_confidence()
            + self.get_velocity_confidence()
            + self.get_rotation_confidence()
        )

    def update_transformation_delta_t_with_size(
        self, new_delta_t: float, size_matrix_w: int, size_matrix_h: int
    ):
        self.F[0][size_matrix_w // 2] = new_delta_t
        self.F[1][size_matrix_h // 2] = new_delta_t
        self.F[0][0] = size_matrix_w
        self.F[1][1] = size_matrix_h
