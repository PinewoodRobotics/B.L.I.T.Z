import math
import numpy as np
from blitz.common.util.math import transform_matrix_to_size, transform_vector_to_size
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
        self.config = config.get_config()

    def get_data_type(self) -> type[OdometryData]:
        return OdometryData

    def get_used_indices(self) -> list[bool]:
        used_indices = []
        used_indices.extend([self.config.use_position] * 2)
        used_indices.extend([True, True])
        used_indices.extend([self.config.use_rotation] * 2)
        return used_indices

    def jacobian_h(self, x: np.ndarray) -> np.ndarray:
        return transform_matrix_to_size(self.get_used_indices(), np.eye(6))

    def hx(self, x: np.ndarray) -> np.ndarray:
        return transform_vector_to_size(x, self.get_used_indices())

    def prepare_input(
        self, data: OdometryData, sensor_id: str, x: np.ndarray | None = None
    ) -> KalmanFilterInput:
        values = []
        if self.config.use_position:
            values.append(data.position.position.x)
            values.append(data.position.position.y)

        values.append(data.velocity.x)
        values.append(data.velocity.y)

        if self.config.use_rotation:
            values.append(data.position.direction.x)
            values.append(data.position.direction.y)

        return KalmanFilterInput(
            input_list=np.array(values),
            sensor_id=sensor_id,
            sensor_type=KalmanFilterSensorType.ODOMETRY,
            jacobian_h=self.jacobian_h,
            hx=self.hx,
        )
