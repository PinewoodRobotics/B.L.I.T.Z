import numpy as np
from blitz.common.config import from_file
from blitz.generated.proto.python.sensor.apriltags_pb2 import AprilTagData
from blitz.generated.proto.python.sensor.imu_pb2 import ImuData
from blitz.generated.proto.python.sensor.odometry_pb2 import OdometryData
from blitz.generated.proto.python.util.position_pb2 import Position3d
from blitz.generated.thrift.config.kalman_filter.ttypes import KalmanFilterSensorType
from blitz.generated.thrift.config.ttypes import Config
from blitz.pos_extrapolator.__tests__.fixtures.shared_resources import (
    set_config_data_preparer_manager,
)
from blitz.pos_extrapolator.data_prep import DataPreparerManager
from blitz.pos_extrapolator.preparers.AprilTagPreparer import AprilTagDataPreparerConfig
from blitz.pos_extrapolator.preparers.ImuDataPreparer import ImuDataPreparerConfig
from blitz.pos_extrapolator.preparers.OdomDataPreparer import OdomDataPreparerConfig


def sample_imu_data():
    imu_data = ImuData()
    imu_data.position.position.x = 1
    imu_data.position.position.y = 2
    imu_data.position.position.z = 3
    imu_data.position.direction.x = 0.5
    imu_data.position.direction.y = 0.5
    imu_data.position.direction.z = 4
    imu_data.acceleration.x = 7
    imu_data.acceleration.y = 8
    imu_data.acceleration.z = 9
    imu_data.velocity.x = 10
    imu_data.velocity.y = 11
    imu_data.velocity.z = 12

    return imu_data


def sample_odometry_data():
    odometry_data = OdometryData()
    odometry_data.position.position.x = 13
    odometry_data.position.position.y = 14
    odometry_data.position.direction.x = 0.7
    odometry_data.position.direction.y = 0.7
    odometry_data.velocity.x = 15
    odometry_data.velocity.y = 16
    return odometry_data


def test_data_prep():
    set_config_data_preparer_manager(
        from_file("src/blitz/pos_extrapolator/__tests__/fixtures/sample_config.txt")
    )
    data_preparer_manager = DataPreparerManager()
    imu_data = sample_imu_data()
    odometry_data = sample_odometry_data()

    imu_input = data_preparer_manager.prepare_data(imu_data, "0")
    odometry_input = data_preparer_manager.prepare_data(odometry_data, "odom")

    assert np.array_equal(
        imu_input.input_list, np.array([1.0, 2.0, 10.0, 11.0, 0.5, 0.5])
    )
    assert imu_input.sensor_id == "0"
    assert imu_input.sensor_type == KalmanFilterSensorType.IMU

    assert np.allclose(
        odometry_input.input_list, [13.0, 14.0, 15.0, 16.0, 0.69999999, 0.69999999]
    )
    assert odometry_input.sensor_id == "odom"
    assert odometry_input.sensor_type == KalmanFilterSensorType.ODOMETRY


def test_get_config():
    DataPreparerManager._config_instances = {}

    config = from_file(
        "src/blitz/pos_extrapolator/__tests__/fixtures/sample_config.txt"
    )

    preparer_manager = DataPreparerManager()

    DataPreparerManager.set_config(
        ImuData, ImuDataPreparerConfig(config.pos_extrapolator.imu_config)
    )

    imu = ImuData()
    odom = OdometryData()

    data_type_name_imu = type(imu).__name__
    data_type_name_odom = type(odom).__name__

    assert data_type_name_imu in preparer_manager._config_instances
    assert data_type_name_odom not in preparer_manager._config_instances

    DataPreparerManager.set_config(
        OdometryData, OdomDataPreparerConfig(config.pos_extrapolator.odom_config)
    )

    assert data_type_name_imu in preparer_manager._registry
    assert data_type_name_odom in preparer_manager._config_instances
