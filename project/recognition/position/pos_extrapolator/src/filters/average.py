from project.common.config_class.filters.kalman_filter_config import MeasurementType
from project.recognition.position.pos_extrapolator.src.filter import FilterStrategy


class AverageFilter(FilterStrategy):
    def __init__(self) -> None:
        super().__init__(None)
        self.data: list[list[float]] = []
        self.estimated_data: list[float] = []

    def filter_data(self, data: list[float], _: MeasurementType) -> None:
        self.data.append(data)
        self.estimated_data = []
        for i in range(len(data)):
            self.estimated_data.append(
                self.get_avg_value_list(self.get_all_sublist_positions(i))
            )

    # we can't tell from avg so :/
    def get_confidence(self) -> float:
        return 1.0

    def get_data(self) -> list[float]:
        return self.estimated_data

    def get_avg_value_list(self, data: list[float]) -> float:
        sum_data = sum(data)
        return 1 if sum_data == 0 else sum_data / len(data)

    def get_all_sublist_positions(self, pos: int) -> list[float]:
        return [sublist[pos] for sublist in self.data]
