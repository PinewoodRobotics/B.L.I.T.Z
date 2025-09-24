import type { KalmanFilterConfig } from "generated/thrift/gen-nodejs/kalman_filter_types";
import { MatrixUtil, VectorUtil } from "../../util/math";
import { KalmanFilterSensorTypeUtil, SensorType } from "../../util/struct";

export const kalman_filter: KalmanFilterConfig = {
  state_vector: VectorUtil.fromArray([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]), // [x, y, vx, vy, cos(theta), sin(theta)]
  time_step_initial: 0.1,
  state_transition_matrix: MatrixUtil.buildMatrixFromDiagonal([
    1, 1, 1, 1, 1, 1,
  ]),
  uncertainty_matrix: MatrixUtil.buildMatrixFromDiagonal([
    10.0, 10.0, 2.0, 2.0, 1.0, 1.0,
  ]),
  process_noise_matrix: MatrixUtil.buildMatrixFromDiagonal([
    0.01, 0.01, 0.1, 0.1, 0.01, 0.01,
  ]),
  dim_x_z: [6, 6],
  sensors: {
    [KalmanFilterSensorTypeUtil.fromEnum(SensorType.APRIL_TAG)]: {
      prod_1: {
        measurement_conversion_matrix: MatrixUtil.buildMatrixFromDiagonal([
          1, 1, 1, 1,
        ]),
        measurement_noise_matrix: MatrixUtil.buildMatrixFromDiagonal([
          5, 5, 1, 1,
        ]),
      },
    },
    [KalmanFilterSensorTypeUtil.fromEnum(SensorType.IMU)]: {
      0: {
        measurement_conversion_matrix: MatrixUtil.buildMatrixFromDiagonal([
          1, 1, 1, 1,
        ]),
        measurement_noise_matrix: MatrixUtil.buildMatrixFromDiagonal([
          100, 100, 0.01, 0.01,
        ]),
      },
    },
    [KalmanFilterSensorTypeUtil.fromEnum(SensorType.ODOM)]: {
      odom: {
        measurement_conversion_matrix: MatrixUtil.buildMatrixFromDiagonal([
          1, 1, 1, 1, 1, 1,
        ]),
        measurement_noise_matrix: MatrixUtil.buildMatrixFromDiagonal([
          0, 5, 0.01, 0.01, 0.2, 0.2,
        ]),
      },
    },
  },
};
