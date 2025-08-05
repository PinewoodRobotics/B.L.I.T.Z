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

    def prepare_input(
        self, data: ImuData, sensor_id: str, x: np.ndarray | None = None
    ) -> KalmanFilterInput:
        config = self.config.config[sensor_id]
        values = [
            (config.use_position, data.position.position.x),
            (config.use_position, data.position.position.y),
            (config.use_velocity, data.velocity.x),
            (config.use_velocity, data.velocity.y),
            (config.use_rotation, data.position.direction.x),
            (config.use_rotation, data.position.direction.y),
        ]

        # Only include values that are used
        used_values = [value for use, value in values]
        non_used_indices = [i for i, (use, _) in enumerate(values) if not use]

        return KalmanFilterInput(
            input_list=np.array(used_values),
            sensor_id=sensor_id,
            sensor_type=KalmanFilterSensorType.IMU,
            non_used_indices=non_used_indices if non_used_indices else None,
        )

    def jacobian_h(self, x: np.ndarray) -> np.ndarray:
        return np.eye(6)

    def hx(self, x: np.ndarray) -> np.ndarray:
        return x
