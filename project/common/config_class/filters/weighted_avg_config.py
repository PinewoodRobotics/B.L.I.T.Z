from pydantic import BaseModel
from typing import Any, Dict


class SensorConfig(BaseModel):
    weight: float


class WeightedAvgConfig(BaseModel):
    sensors: dict[str, SensorConfig]

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "WeightedAvgConfig":
        sensors_config = {
            sensor: SensorConfig(**config[sensor]) for sensor in config["sensors"]
        }

        return cls(sensors=sensors_config)
