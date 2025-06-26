import json
import pytest
from blitz.common.config import from_file
from blitz.generated.proto.python.sensor.apriltags_pb2 import AprilTagData
from blitz.generated.proto.python.sensor.imu_pb2 import ImuData
from blitz.generated.proto.python.sensor.odometry_pb2 import OdometryData
from blitz.generated.thrift.config.ttypes import Config
from blitz.pos_extrapolator.data_prep import DataPreparerManager
from blitz.pos_extrapolator.preparers.AprilTagPreparer import AprilTagDataPreparerConfig
from blitz.pos_extrapolator.preparers.ImuDataPreparer import ImuDataPreparerConfig
from blitz.pos_extrapolator.preparers.OdomDataPreparer import OdomDataPreparerConfig


def set_config_data_preparer_manager(config: Config):
    DataPreparerManager.set_config(
        ImuData, ImuDataPreparerConfig(config.pos_extrapolator.imu_config)
    )
    DataPreparerManager.set_config(
        OdometryData, OdomDataPreparerConfig(config.pos_extrapolator.odom_config)
    )
    DataPreparerManager.set_config(
        AprilTagData,
        AprilTagDataPreparerConfig(
            (
                config.pos_extrapolator.tag_position_config,
                config.pos_extrapolator.camera_position_config,
            ),
        ),
    )
