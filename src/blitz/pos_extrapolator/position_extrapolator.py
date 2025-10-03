import time

import numpy as np
from blitz.common.debug.logger import info
from blitz.generated.proto.python.util.position_pb2 import RobotPosition
from blitz.generated.proto.python.util.vector_pb2 import Vector2, Vector3
from blitz.generated.thrift.config.camera.ttypes import CameraParameters
from blitz.generated.thrift.config.common.ttypes import Point3
from blitz.generated.thrift.config.kalman_filter.ttypes import KalmanFilterSensorType
from blitz.generated.thrift.config.pos_extrapolator.ttypes import (
    ImuConfig,
    OdomConfig,
    PosExtrapolator,
    TagUseImuRotation,
)
from blitz.pos_extrapolator.data_prep import DataPreparerManager, ExtrapolationContext
from blitz.pos_extrapolator.filter_strat import GenericFilterStrategy


class PositionExtrapolator:
    CAMERA_OUTPUT_TO_ROBOT_ROTATION = np.array(
        [
            [0, 0, 1],
            [-1, 0, 0],
            [0, 1, 0],
        ]
    )

    def __init__(
        self,
        config: PosExtrapolator,
        filter_strategy: GenericFilterStrategy,
        data_preparer_manager: DataPreparerManager,
    ):
        self.config = config
        self.filter_strategy = filter_strategy
        self.data_preparer_manager = data_preparer_manager
        self.last_predict = time.time()
        self.has_gotten_rotation = (
            self.config.tag_use_imu_rotation == TagUseImuRotation.NEVER
        )

    def insert_sensor_data(self, data: object, sensor_id: str) -> None:
        context = ExtrapolationContext(
            x=self.filter_strategy.get_state(),
            has_gotten_rotation=self.has_gotten_rotation,
        )

        prepared_data = self.data_preparer_manager.prepare_data(
            data, sensor_id, context=context
        )

        if prepared_data is None:
            return

        if self.is_rotation_gotten(prepared_data.sensor_type, sensor_id):
            self.has_gotten_rotation = True

        self.filter_strategy.insert_data(prepared_data)

    def is_rotation_gotten(
        self, sensor_type: KalmanFilterSensorType, sensor_id: str
    ) -> bool:
        if sensor_type == KalmanFilterSensorType.APRIL_TAG:
            return False

        if sensor_type == KalmanFilterSensorType.ODOMETRY:
            return self.config.odom_config.use_rotation

        if sensor_type == KalmanFilterSensorType.IMU:
            return self.config.imu_config[sensor_id].use_rotation

        return True

    def get_robot_position_estimate(self) -> list[float]:
        return self.filter_strategy.get_state().flatten().tolist()

    def get_robot_position(self) -> RobotPosition:
        filtered_position = self.get_robot_position_estimate()
        proto_position = RobotPosition()
        proto_position.timestamp = time.time() * 1000
        proto_position.confidence = self.get_confidence()
        proto_position.position_2d.position.x = filtered_position[0]
        proto_position.position_2d.position.y = filtered_position[1]
        proto_position.position_2d.direction.x = filtered_position[4]
        proto_position.position_2d.direction.y = filtered_position[5]
        proto_position.P.extend(self.get_position_covariance())

        return proto_position

    def get_confidence(self) -> float:
        return self.filter_strategy.get_confidence()

    def get_position_covariance(self) -> list[float]:
        return self.filter_strategy.get_P().flatten().tolist()
