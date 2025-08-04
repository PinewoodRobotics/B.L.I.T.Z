import time
from typing import Optional
from filterpy.kalman import ExtendedKalmanFilter
import numpy as np
import warnings

from blitz.common.util.math import get_np_from_matrix
from blitz.generated.thrift.config.kalman_filter.ttypes import (
    KalmanFilterConfig,
)
from blitz.pos_extrapolator.data_prep import KalmanFilterInput
from blitz.pos_extrapolator.filter_strat import GenericFilterStrategy


# x, y, vx, vy, cos(theta), sin(theta)
class ExtendedKalmanFilterStrategy(ExtendedKalmanFilter, GenericFilterStrategy):
    def __init__(self, config: KalmanFilterConfig):
        super().__init__(dim_x=config.dim_x_z[0], dim_z=config.dim_x_z[1])
        self.hw = config.dim_x_z[0]

        self.x = np.array(config.state_vector, dtype=np.float64)
        self.P = np.array(config.uncertainty_matrix, dtype=np.float64)
        self.Q = np.array(config.process_noise_matrix, dtype=np.float64)
        self.F = np.array(config.state_transition_matrix, dtype=np.float64)
        self.config = config

        self._normalize_state()
        self._ensure_matrix_properties()

        self.max_covariance_trace = 1e6
        self.min_eigenvalue_threshold = 1e-12

        self.last_update_time = time.time()

    def _normalize_state(self):
        if len(self.x) >= 6:
            cos_theta = self.x[4]
            sin_theta = self.x[5]
            norm = np.sqrt(cos_theta**2 + sin_theta**2)
            if norm > 0 and abs(norm - 1.0) > 1e-10:
                self.x[4] /= norm
                self.x[5] /= norm

    def _ensure_matrix_properties(self):
        self.P = self._make_positive_definite(self.P)
        self.Q = self._make_positive_definite(self.Q)

    def _make_positive_definite(
        self, matrix: np.ndarray, min_eigenvalue: float = 1e-12
    ) -> np.ndarray:
        eigenvalues, eigenvectors = np.linalg.eigh(matrix)
        eigenvalues = np.maximum(eigenvalues, min_eigenvalue)
        return eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T

    def _check_divergence(self) -> bool:
        trace = np.trace(self.P)
        if trace > self.max_covariance_trace:
            warnings.warn(f"Filter may be diverging: covariance trace = {trace}")
            return True

        eigenvalues = np.linalg.eigvals(self.P)
        if np.any(eigenvalues <= 0):
            warnings.warn("Covariance matrix has non-positive eigenvalues")
            return True

        return False

    def jacobian_h(self, x: np.ndarray) -> np.ndarray:
        return np.array(
            [
                [1, 0, 0, 0, 0, 0],  # x
                [0, 1, 0, 0, 0, 0],  # y
                [0, 0, 1, 0, 0, 0],  # vx
                [0, 0, 0, 1, 0, 0],  # vy
                [0, 0, 0, 0, 1, 0],  # cos(theta)
                [0, 0, 0, 0, 0, 1],  # sin(theta)
            ]
        )

    def hx(self, x: np.ndarray, non_used_indices: Optional[list[int]]) -> np.ndarray:
        if non_used_indices is not None:
            mask = [i for i in range(len(x)) if i not in non_used_indices]
            return x[mask]

        return x

    def insert_data(self, data: KalmanFilterInput) -> None:
        dt = time.time() - self.last_update_time
        if dt > 1 or dt < 0:
            warnings.warn(f"Invalid delta_t: {dt}. Must be between 0 and 1.")
            dt = 0.05

        self._update_transformation_delta_t_with_size(
            dt,
            self.hw,
            self.hw,
        )

        self.predict()
        self._normalize_state()

        R = get_np_from_matrix(
            self.config.sensors[data.sensor_type][
                data.sensor_id
            ].measurement_noise_matrix
        )
        R = self._make_positive_definite(R)

        self.update(
            data.input_list,
            self.jacobian_h,
            self.hx,
            R=R,
            hx_args=(data.non_used_indices,),
        )

        self.last_update_time = time.time()

        self._normalize_state()
        self.P = self._make_positive_definite(self.P)
        self._check_divergence()

    def get_state(self) -> list[float]:
        return [float(x) for x in self.x.flatten()]

    def get_position_confidence(self) -> float:
        P_position = self.P[:2, :2]
        eigenvalues = np.linalg.eigvals(P_position)
        return 1.0 / (1.0 + np.sqrt(np.max(eigenvalues)))

    def get_velocity_confidence(self) -> float:
        P_velocity = self.P[2:4, 2:4]
        eigenvalues = np.linalg.eigvals(P_velocity)
        return 1.0 / (1.0 + np.sqrt(np.max(eigenvalues)))

    def get_rotation_confidence(self) -> float:
        angle_uncertainty = np.sqrt(self.P[4, 4] + self.P[5, 5])
        return 1.0 / (1.0 + angle_uncertainty)

    def get_confidence(self) -> float:
        pos_conf = self.get_position_confidence()
        vel_conf = self.get_velocity_confidence()
        rot_conf = self.get_rotation_confidence()
        return (pos_conf * vel_conf * rot_conf) ** (1 / 3)

    def _update_transformation_delta_t_with_size(
        self, new_delta_t: float, size_matrix_w: int, size_matrix_h: int
    ):
        if new_delta_t <= 0:
            warnings.warn(f"Invalid delta_t: {new_delta_t}. Must be positive.")
            return

        if size_matrix_w <= 0 or size_matrix_h <= 0:
            warnings.warn(f"Invalid matrix dimensions: {size_matrix_w}x{size_matrix_h}")
            return

        try:
            vel_idx_x = size_matrix_w // 2
            vel_idx_y = size_matrix_h // 2

            if (
                vel_idx_x < self.F.shape[1]
                and vel_idx_y < self.F.shape[1]
                and vel_idx_x >= 0
                and vel_idx_y >= 0
            ):
                self.F[0][vel_idx_x] = new_delta_t
                self.F[1][vel_idx_y] = new_delta_t
                self.F[0][0] = size_matrix_w
                self.F[1][1] = size_matrix_h
            else:
                warnings.warn(f"Matrix index out of bounds for F matrix update")
        except IndexError as e:
            warnings.warn(f"Error updating F matrix: {e}")

    def reset_filter_on_divergence(self):
        if self._check_divergence():
            warnings.warn("Resetting filter due to divergence")
            self.P = np.eye(self.P.shape[0]) * 1e-3
            self._normalize_state()
            return True
        return False

    def get_P(self) -> np.ndarray | None:
        return self.P
