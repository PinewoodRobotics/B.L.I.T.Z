from project.common.config_class.filters.kalman_filter_config import (
    MeasurementType,
)


class FilterStrategy:
    def __init__(self, config):
        self.config = config

    def filter_data(self, data: list[float], data_type: MeasurementType) -> None:
        raise NotImplementedError("Subclasses must implement filter_data()")

    def get_confidence(self) -> float:
        raise NotImplementedError("Subclasses must implement get_confidence()")

    def get_filtered_data(self) -> list[float]:
        raise NotImplementedError("Subclasses must implement get_filtered_data()")
