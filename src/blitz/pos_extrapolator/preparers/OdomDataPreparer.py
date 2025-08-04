import math
import numpy as np
from blitz.generated.proto.python.sensor.imu_pb2 import ImuData
from blitz.generated.proto.python.sensor.odometry_pb2 import OdometryData
from blitz.generated.thrift.config.kalman_filter.ttypes import KalmanFilterSensorType
from blitz.generated.thrift.config.pos_extrapolator.ttypes import ImuConfig, OdomConfig
from blitz.pos_extrapolator.data_prep import (
    ConfigProvider,
    DataPreparer,
    DataPreparerManager,
    KalmanFilterInput,
)


class OdomDataPreparerConfig(ConfigProvider[OdomConfig]):
    def __init__(self, config: OdomConfig):
        self.config = config

    def get_config(self) -> OdomConfig:
        return self.config


@DataPreparerManager.register(proto_type=OdometryData)
class OdomDataPreparer(DataPreparer[OdometryData, OdomDataPreparerConfig]):
    def __init__(self, config: OdomDataPreparerConfig):
        super().__init__(config)

    def get_data_type(self) -> type[OdometryData]:
        return OdometryData

    def prepare_input(self, data: OdometryData, sensor_id: str) -> KalmanFilterInput:
        return KalmanFilterInput(
            input_list=np.array(
                [
                    data.position.position.x,
                    data.position.position.y,
                    data.velocity.x,
                    data.velocity.y,
                    data.position.direction.x,
                    data.position.direction.y,
                ]
            ),
            sensor_id=sensor_id,
            sensor_type=KalmanFilterSensorType.ODOMETRY,
        )
