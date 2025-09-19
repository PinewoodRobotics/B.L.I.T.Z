from dataclasses import dataclass, field
from typing import Any, Dict, Type, TypeVar, Optional, Callable, Protocol

import numpy as np
from numpy.typing import NDArray

from blitz.generated.thrift.config.kalman_filter.ttypes import KalmanFilterSensorType

T = TypeVar("T")
C = TypeVar("C", covariant=True)


@dataclass
class KalmanFilterInput:
    input_list: NDArray[np.float64]
    sensor_id: str
    sensor_type: KalmanFilterSensorType
    jacobian_h: Callable[[NDArray[np.float64]], NDArray[np.float64]] | None = None
    hx: Callable[[NDArray[np.float64]], NDArray[np.float64]] | None = None


class ConfigProvider(Protocol[C]):
    def get_config(self) -> C: ...


class DataPreparer(Protocol[T, C]):
    def __init__(self, config: C | None = None):
        pass

    def prepare_input(
        self, data: T, sensor_id: str, x: NDArray[np.float64] | None = None
    ) -> KalmanFilterInput: ...

    def get_data_type(self) -> type[T]: ...


class DataPreparerManager:
    _registry: dict[str, type[DataPreparer[Any, Any]]] = {}
    _config_instances: dict[str, Any] = {}

    @classmethod
    def register(cls, proto_type: Type[T], config_instance: Any = None):
        def decorator(preparer_class: Type[DataPreparer[T, Any]]):
            cls._registry[proto_type.__name__] = preparer_class
            if config_instance is not None:
                cls._config_instances[proto_type.__name__] = config_instance
            return preparer_class

        return decorator

    @classmethod
    def set_config(cls, proto_type: type[T], config_instance: Any):
        cls._config_instances[proto_type.__name__] = config_instance

    def prepare_data(
        self, data: object, sensor_id: str, x: NDArray[np.float64] | None = None
    ) -> KalmanFilterInput:
        data_type_name = type(data).__name__

        if data_type_name not in self._registry:
            raise ValueError(f"No preparer registered for data type: {data_type_name}")

        preparer_class = self._registry[data_type_name]
        config_instance = self._config_instances.get(data_type_name)
        preparer_instance = preparer_class(config_instance)

        return preparer_instance.prepare_input(data, sensor_id, x)
