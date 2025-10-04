import json
import pytest
from backend.python.common.config import from_file
from backend.generated.proto.python.sensor.apriltags_pb2 import AprilTagData
from backend.generated.proto.python.sensor.imu_pb2 import ImuData
from backend.generated.proto.python.sensor.odometry_pb2 import OdometryData
from backend.generated.thrift.config.ttypes import Config
from backend.python.pos_extrapolator.data_prep import DataPreparerManager
from backend.python.pos_extrapolator.preparers.AprilTagPreparer import (
    AprilTagConfig,
    AprilTagDataPreparerConfig,
)
from backend.python.pos_extrapolator.preparers.ImuDataPreparer import (
    ImuDataPreparerConfig,
)
from backend.python.pos_extrapolator.preparers.OdomDataPreparer import (
    OdomDataPreparerConfig,
)


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
            AprilTagConfig(
                config.pos_extrapolator.tag_position_config,
                config.pos_extrapolator.camera_position_config,
                config.pos_extrapolator.tag_use_imu_rotation,
            ),
        ),
    )
