from typing import final
import numpy as np
from numpy.typing import NDArray
from blitz.common.util.math import transform_matrix_to_size, transform_vector_to_size
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
        self.config: ImuDataPreparerConfig = config

    def get_data_type(self) -> type[ImuData]:
        return ImuData

    def get_used_indices(self, sensor_id: str) -> list[bool]:
        used_indices: list[bool] = []
        used_indices.extend([self.config.config[sensor_id].use_position] * 2)
        used_indices.extend([self.config.config[sensor_id].use_velocity] * 2)
        used_indices.extend([self.config.config[sensor_id].use_rotation] * 2)
        return used_indices

    def jacobian_h(self, x: NDArray[np.float64], sensor_id: str) -> NDArray[np.float64]:
        return transform_matrix_to_size(self.get_used_indices(sensor_id), np.eye(6))

    def hx(self, x: NDArray[np.float64], sensor_id: str) -> NDArray[np.float64]:
        return transform_vector_to_size(x, self.get_used_indices(sensor_id))

    def prepare_input(
        self, data: ImuData, sensor_id: str, x: NDArray[np.float64] | None = None
    ) -> KalmanFilterInput | None:
        config = self.config.config[sensor_id]
        values: list[float] = []

        if config.use_position:
            values.append(data.position.position.x)
            values.append(data.position.position.y)
        if config.use_velocity:
            values.append(data.velocity.x)
            values.append(data.velocity.y)
        if config.use_rotation:
            values.append(data.position.direction.x)
            values.append(data.position.direction.y)

        return KalmanFilterInput(
            input_list=np.array(values),
            sensor_id=sensor_id,
            sensor_type=KalmanFilterSensorType.IMU,
            jacobian_h=lambda x: self.jacobian_h(x, sensor_id),
            hx=lambda x: self.hx(x, sensor_id),
        )
