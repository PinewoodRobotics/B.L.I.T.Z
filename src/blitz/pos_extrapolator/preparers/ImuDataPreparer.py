import numpy as np
from blitz.generated.proto.python.sensor.imu_pb2 import ImuData
from blitz.generated.thrift.config.kalman_filter.ttypes import KalmanFilterSensorType
from blitz.generated.thrift.config.pos_extrapolator.ttypes import ImuConfig
from blitz.pos_extrapolator.data_prep import (
    ConfigProvider,
    DataPreparer,
    DataPreparerManager,
    KalmanFilterInput,
)


class ImuDataPreparerConfig(ConfigProvider[dict[str, ImuConfig]]):
    def __init__(self, config: dict[str, ImuConfig]):
        self.config = config

    def get_config(self) -> dict[str, ImuConfig]:
        return self.config


@DataPreparerManager.register(proto_type=ImuData)
class ImuDataPreparer(DataPreparer[ImuData, ImuDataPreparerConfig]):
    def __init__(self, config: ImuDataPreparerConfig):
        super().__init__(config)
        self.config = config

    def get_data_type(self) -> type[ImuData]:
        return ImuData

    def prepare_input(self, data: ImuData, sensor_id: str) -> KalmanFilterInput:
        return KalmanFilterInput(
            input_list=np.array(
                [
                    data.position.position.x,
                    data.position.position.y,
                    data.position.position.z,
                    data.velocity.x,
                    data.velocity.y,
                    data.acceleration.x,
                    data.acceleration.y,
                ]
            ),
            sensor_id=sensor_id,
            sensor_type=KalmanFilterSensorType.IMU,
        )
