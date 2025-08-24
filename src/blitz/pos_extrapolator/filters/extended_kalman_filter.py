import time
from typing import Optional
from filterpy.kalman import ExtendedKalmanFilter
import numpy as np
import warnings

from blitz.common.util.math import get_np_from_matrix, get_np_from_vector
from blitz.generated.thrift.config.kalman_filter.ttypes import (
    KalmanFilterConfig,
    KalmanFilterSensorType,
)
from blitz.pos_extrapolator.data_prep import KalmanFilterInput
from blitz.pos_extrapolator.filter_strat import GenericFilterStrategy


class ExtendedKalmanFilterStrategy(ExtendedKalmanFilter, GenericFilterStrategy):
    def __init__(
        self,
        config: KalmanFilterConfig,
        fake_dt: float | None = None,
    ):
        super().__init__(dim_x=config.dim_x_z[0], dim_z=config.dim_x_z[1])
        self.hw = config.dim_x_z[0]
        self.x = get_np_from_vector(config.state_vector)
        self.P = get_np_from_matrix(config.uncertainty_matrix)
        self.Q = get_np_from_matrix(config.process_noise_matrix)
        self.F = get_np_from_matrix(config.state_transition_matrix)
        self.config = config
        self.R_sensors = self.get_R_sensors(config)
        self.last_update_time = time.time()
        self.fake_dt = fake_dt

    def get_R_sensors(
        self, config: KalmanFilterConfig
    ) -> dict[KalmanFilterSensorType, dict[str, np.ndarray]]:
        output = {}
        for sensor_type in config.sensors:
            for sensor_id in config.sensors[sensor_type]:
                numpy_arr = get_np_from_matrix(
                    config.sensors[sensor_type][sensor_id].measurement_noise_matrix
                )

                # select rows and cols with > 0 sum
                numpy_arr = numpy_arr[abs(np.sum(numpy_arr, axis=1)) > 0, :]
                numpy_arr = numpy_arr[:, abs(np.sum(numpy_arr, axis=0)) > 0]

                output[sensor_type] = output.get(sensor_type, {})
                output[sensor_type][sensor_id] = numpy_arr

        return output

    def jacobian_h(self, x: np.ndarray) -> np.ndarray:
        return np.eye(6)

    def hx(self, x: np.ndarray) -> np.ndarray:
        return x

    def insert_data(self, data: KalmanFilterInput) -> None:
        if self.fake_dt is not None:
            dt = self.fake_dt
        else:
            dt = time.time() - self.last_update_time

        if dt > 5 or dt < 0:
            dt = 0.05

        self._update_transformation_delta_t_with_size(dt)

        self.predict()

        R = self.R_sensors[data.sensor_type][data.sensor_id]

        self.update(
            data.input_list,
            data.jacobian_h if data.jacobian_h is not None else self.jacobian_h,
            data.hx if data.hx is not None else self.hx,
            R=R,
        )

        self.last_update_time = time.time()

    def get_state(self) -> np.ndarray:
        return self.x

    def get_position_confidence(self) -> float:
        P_position = self.P[:2, :2]
        if np.any(np.isnan(P_position)) or np.any(np.isinf(P_position)):
            return 0.0
        try:
            eigenvalues = np.linalg.eigvals(P_position)
            max_eigen = np.max(eigenvalues)
            if np.isnan(max_eigen) or np.isinf(max_eigen) or max_eigen < 0:
                return 0.0
            return 1.0 / (1.0 + np.sqrt(max_eigen))
        except np.linalg.LinAlgError:
            return 0.0

    def get_velocity_confidence(self) -> float:
        P_velocity = self.P[2:4, 2:4]
        if np.any(np.isnan(P_velocity)) or np.any(np.isinf(P_velocity)):
            return 0.0
        try:
            eigenvalues = np.linalg.eigvals(P_velocity)
            max_eigen = np.max(eigenvalues)
            if np.isnan(max_eigen) or np.isinf(max_eigen) or max_eigen < 0:
                return 0.0
            return 1.0 / (1.0 + np.sqrt(max_eigen))
        except np.linalg.LinAlgError:
            return 0.0

    def get_rotation_confidence(self) -> float:
        angle_var = self.P[4, 4] + self.P[5, 5]
        if np.isnan(angle_var) or np.isinf(angle_var) or angle_var < 0:
            return 0.0
        angle_uncertainty = np.sqrt(angle_var)
        return 1.0 / (1.0 + angle_uncertainty)

    def get_confidence(self) -> float:
        pos_conf = self.get_position_confidence()
        vel_conf = self.get_velocity_confidence()
        rot_conf = self.get_rotation_confidence()
        if pos_conf == 0.0 or vel_conf == 0.0 or rot_conf == 0.0:
            return 0.0
        return (pos_conf * vel_conf * rot_conf) ** (1 / 3)

    def _update_transformation_delta_t_with_size(self, new_delta_t: float):
        try:
            vel_idx_x = 2  # vx is at index 2 in [x, y, vx, vy, theta, omega]
            vel_idx_y = 3  # vy is at index 3 in [x, y, vx, vy, theta, omega]
            self.F[0][vel_idx_x] = new_delta_t
            self.F[1][vel_idx_y] = new_delta_t
        except IndexError as e:
            warnings.warn(f"Error updating F matrix: {e}")
