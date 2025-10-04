from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray

from backend.python.pos_extrapolator.data_prep import (
    ExtrapolationContext,
    KalmanFilterInput,
)


class GenericFilterStrategy:
    def insert_data(self, data: KalmanFilterInput) -> None:
        raise NotImplementedError("insert_data not implemented")

    def get_state(self) -> NDArray[np.float64]:
        raise NotImplementedError("get_state not implemented")

    def get_confidence(self) -> float:
        raise NotImplementedError("get_confidence not implemented")

    def get_P(self) -> NDArray[np.float64]:
        # only for kalman filters and usually for debugging purposes
        return np.array([])

    def _debug_set_state(self, x: NDArray[np.float64]) -> None:
        pass
