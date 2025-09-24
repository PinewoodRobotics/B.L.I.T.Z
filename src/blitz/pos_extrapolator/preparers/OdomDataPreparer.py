import math
import numpy as np
from numpy.typing import NDArray
from blitz.common.util.math import transform_matrix_to_size, transform_vector_to_size
from blitz.generated.proto.python.sensor.imu_pb2 import ImuData
from blitz.generated.proto.python.sensor.odometry_pb2 import OdometryData
from blitz.generated.thrift.config.kalman_filter.ttypes import KalmanFilterSensorType
from blitz.generated.thrift.config.pos_extrapolator.ttypes import ImuConfig, OdomConfig
from blitz.pos_extrapolator.data_prep import (
    ConfigProvider,
    DataPreparer,
    DataPreparerManager,
    ExtrapolationContext,
    KalmanFilterInput,
)


class OdomDataPreparerConfig(ConfigProvider[OdomConfig]):
    def __init__(self, config: OdomConfig):
        self.config = config

    def get_config(self) -> OdomConfig:
        return self.config


SHOULD_USE_ROTATION_MATRIX = False


@DataPreparerManager.register(proto_type=OdometryData)
class OdomDataPreparer(DataPreparer[OdometryData, OdomDataPreparerConfig]):
    def __init__(self, config: OdomDataPreparerConfig):
        super().__init__(config)
        self.config = config.get_config()

    def get_data_type(self) -> type[OdometryData]:
        return OdometryData

    def get_used_indices(self) -> list[bool]:
        used_indices: list[bool] = []
        used_indices.extend([self.config.use_position] * 2)
        used_indices.extend([True, True])
        used_indices.extend([self.config.use_rotation] * 2)
        return used_indices

    def jacobian_h(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        return transform_matrix_to_size(self.get_used_indices(), np.eye(6))

    def hx(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        return transform_vector_to_size(x, self.get_used_indices())

    def prepare_input(
        self,
        data: OdometryData,
        sensor_id: str,
        context: ExtrapolationContext | None = None,
    ) -> KalmanFilterInput | None:
        assert context is not None
        cos = context.x[4]
        sin = context.x[5]
        rotation_matrix = np.array([[cos, -sin], [sin, cos]])

        vel = np.array([data.velocity.x, data.velocity.y])
        if SHOULD_USE_ROTATION_MATRIX:
            vel = rotation_matrix @ vel

        values: list[float] = []
        if self.config.use_position:
            values.append(data.position.position.x)
            values.append(data.position.position.y)

        values.append(vel[0])
        values.append(vel[1])

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
