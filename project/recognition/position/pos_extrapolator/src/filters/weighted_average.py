from project.common.config_class.filters.kalman_filter_config import MeasurementType
from project.common.config_class.filters.weighted_avg_config import WeightedAvgConfig
from project.recognition.position.pos_extrapolator.src.filter import FilterStrategy


class WeightedAverageFilter(FilterStrategy):
    """
    Basic weighted average filter. Essentially you input a bunch of data and it outputs a weighted avg of the position.
    """

    def __init__(self, config: WeightedAvgConfig) -> None:
        super().__init__(config)
        self.config = config
        self.data: list[tuple[list[float], float]] = []
        self.estimated_data: list[float] = []

    def filter_data(self, data: list[float], data_type: MeasurementType) -> None:
        self.data.append((data, self.config.sensors_config[data_type].weight))
        # Calculate weighted average for each position in the data arrays
        self.estimated_data = []
        for i in range(len(data)):
            point_data = [(d[0][i], d[1]) for d in self.data]
            self.estimated_data.append(self.calculate_weighted_average(point_data))

    def get_confidence(self) -> float:
        return 1.0

    def calculate_weighted_average(self, data: list[tuple[float, float]]) -> float:
        if not data:
            return 0

        values = [x[0] for x in data]
        weights = [x[1] for x in data]

        weight_sum = sum(weights)

        if weight_sum == 0:
            return values[0] if values else 0

        weighted_avg = (
            sum(value * weight for value, weight in zip(values, weights)) / weight_sum
        )

        return weighted_avg
