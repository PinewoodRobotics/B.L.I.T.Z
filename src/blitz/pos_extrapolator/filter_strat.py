import numpy as np


class GenericFilterStrategy:
    def __init__(self):
        pass

    def insert_data(self, data: object) -> None:
        raise NotImplementedError("insert_data not implemented")

    def get_state(self) -> list[float]:
        raise NotImplementedError("get_state not implemented")

    def get_confidence(self) -> float:
        raise NotImplementedError("get_confidence not implemented")

    def get_P(self) -> np.ndarray:
        # only for kalman filters and usually for debugging purposes
        return np.array([])
