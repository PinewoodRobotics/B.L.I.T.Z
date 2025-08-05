import time

import numpy as np
from blitz.generated.proto.python.util.vector_pb2 import Vector3
from blitz.generated.thrift.config.camera.ttypes import CameraParameters
from blitz.generated.thrift.config.common.ttypes import Point3
from blitz.generated.thrift.config.pos_extrapolator.ttypes import (
    ImuConfig,
    OdomConfig,
    PosExtrapolator,
)
from blitz.pos_extrapolator.data_prep import DataPreparerManager
from blitz.pos_extrapolator.filter_strat import GenericFilterStrategy


class PositionExtrapolator:
    CAMERA_OUTPUT_TO_ROBOT_ROTATION = np.array(
        [
            [0, 0, 1],
            [-1, 0, 0],
            [0, -1, 0],
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

    def insert_sensor_data(self, data: object, sensor_id: str) -> None:
        data_preparer = self.data_preparer_manager.prepare_data(
            data, sensor_id, x=self.filter_strategy.get_state()
        )
        self.filter_strategy.insert_data(data_preparer)

    def get_robot_position_estimate(self) -> list[float]:
        return self.filter_strategy.get_state().flatten().tolist()

    def get_confidence(self) -> float:
        return self.filter_strategy.get_confidence()

    def get_position_covariance(self) -> list[float]:
        return self.filter_strategy.get_P().flatten().tolist()
