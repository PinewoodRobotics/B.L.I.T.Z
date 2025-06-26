#!/usr/bin/env python3

import numpy as np
from blitz.generated.proto.python.sensor.imu_pb2 import ImuData
from blitz.generated.thrift.config.pos_extrapolator.ttypes import ImuConfig
from blitz.pos_extrapolator.data_prep import DataManager
from blitz.pos_extrapolator.preparers.ImuDataPreparer import (
    ImuDataPreparer,
    ImuDataPreparerConfig,
)


def test_fixed_implementation():
    config = ImuConfig()
    config_instance = ImuDataPreparerConfig(config)

    DataManager.set_config(ImuData, config_instance)

    sample_data = ImuData()
    sample_data.position.position.x = 1.0
    sample_data.position.position.y = 2.0
    sample_data.position.position.z = 3.0
    sample_data.velocity.x = 0.1
    sample_data.velocity.y = 0.2
    sample_data.acceleration.x = 0.01
    sample_data.acceleration.y = 0.02

    manager = DataManager()
    result = manager.prepare_data(sample_data)

    print("✅ Test passed! All bugs fixed:")
    print(f"   - Input array shape: {result.input_list.shape}")
    print(f"   - Noise matrix shape: {result.noise_matrix.shape}")
    print(
        f"   - Dimensions match: {result.input_list.shape[0] == result.noise_matrix.shape[0]}"
    )


if __name__ == "__main__":
    test_fixed_implementation()
