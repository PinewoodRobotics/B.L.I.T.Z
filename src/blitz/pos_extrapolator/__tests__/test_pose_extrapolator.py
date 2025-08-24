import time
from blitz.common.config import from_file
from blitz.generated.proto.python.sensor.imu_pb2 import ImuData
from blitz.generated.thrift.config.ttypes import Config
from blitz.pos_extrapolator.data_prep import DataPreparerManager
from blitz.pos_extrapolator.filters.extended_kalman_filter import (
    ExtendedKalmanFilterStrategy,
)
from blitz.pos_extrapolator.position_extrapolator import PositionExtrapolator
from blitz.pos_extrapolator.preparers.ImuDataPreparer import ImuDataPreparerConfig
import numpy as np


def initialize(config: Config):
    DataPreparerManager.set_config(
        ImuData, ImuDataPreparerConfig(config.pos_extrapolator.imu_config)
    )

    return PositionExtrapolator(
        config.pos_extrapolator,
        ExtendedKalmanFilterStrategy(config.pos_extrapolator.kalman_filter_config),
        DataPreparerManager(),
    )


def get_sample_imu_data():
    imu_data = ImuData()
    imu_data.velocity.x = 1.0
    imu_data.velocity.y = 2.0
    imu_data.velocity.z = 3.0
    imu_data.position.direction.x = np.cos(np.pi / 4)
    imu_data.position.direction.y = np.sin(np.pi / 4)

    return imu_data


def test_pose_extrapolator():
    config = from_file(
        "src/blitz/pos_extrapolator/__tests__/fixtures/sample_config.txt"
    )

    position_extrapolator = initialize(config)

    position_extrapolator.insert_sensor_data(get_sample_imu_data(), "0")
    time.sleep(1)
    position_extrapolator.insert_sensor_data(get_sample_imu_data(), "0")

    pos = position_extrapolator.get_robot_position()

    assert abs(pos.position_2d.position.x - 1.0) < 0.1
    assert abs(pos.position_2d.position.y - 2.0) < 0.1
    assert abs(pos.position_2d.direction.x - np.cos(np.pi / 4)) < 0.1
    assert abs(pos.position_2d.direction.y - np.sin(np.pi / 4)) < 0.1
