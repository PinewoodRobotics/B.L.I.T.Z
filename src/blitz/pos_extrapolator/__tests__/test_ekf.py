import time
from blitz.common.config import from_file
from blitz.generated.thrift.config.kalman_filter.ttypes import KalmanFilterSensorType
from blitz.pos_extrapolator.data_prep import KalmanFilterInput
from blitz.pos_extrapolator.filters.extended_kalman_filter import (
    ExtendedKalmanFilterStrategy,
)
import numpy as np


def ekf_dataset_imu_input():
    return [
        KalmanFilterInput(
            input_list=np.array([0, 0, 1, 1, 0, 0]),
            sensor_id="imu",
            sensor_type=KalmanFilterSensorType.IMU,
            non_used_indices=[0, 1, 4, 5],
        ),
        KalmanFilterInput(
            input_list=np.array([0, 0, 1, 1, 0, 0]),
            sensor_id="imu",
            sensor_type=KalmanFilterSensorType.IMU,
            non_used_indices=[0, 1, 4, 5],
        ),
        KalmanFilterInput(
            input_list=np.array([0, 0, 1, 1, 0, 0]),
            sensor_id="imu",
            sensor_type=KalmanFilterSensorType.IMU,
            non_used_indices=[0, 1, 4, 5],
        ),
    ]


def test_ekf():
    config = from_file(
        "src/blitz/pos_extrapolator/__tests__/fixtures/sample_config.txt"
    )

    ekf = ExtendedKalmanFilterStrategy(
        config.pos_extrapolator.kalman_filter_config, fake_dt=1
    )
    for input in ekf_dataset_imu_input():
        ekf.insert_data(input)

    state = ekf.get_state()
    print(state)

    # Check that the state is close to expected values (accounting for noise)
    # Logic: Start at [0,0,0,0,0,0], measure vx=1,vy=1, predict 1s -> [1,1,1,1,0,0]
    expected = [3, 3, 1, 1, 0, 0]
    assert len(state) == len(expected)
    for i, (actual, exp) in enumerate(zip(state, expected)):
        assert abs(actual - exp) < 0.1, f"State[{i}]: expected {exp}, got {actual}"


def test_ekf_timing():
    config = from_file(
        "src/blitz/pos_extrapolator/__tests__/fixtures/sample_config.txt"
    )

    ekf = ExtendedKalmanFilterStrategy(
        config.pos_extrapolator.kalman_filter_config, fake_dt=1
    )
    avg_time = 0
    for input in ekf_dataset_imu_input():
        start_time = time.time()
        ekf.insert_data(input)
        end_time = time.time()
        avg_time += end_time - start_time

    avg_time /= len(ekf_dataset_imu_input())
    print(f"Average time per insert: {avg_time} seconds")

    assert avg_time < 0.01
