import type { KalmanFilterConfig } from "generated/thrift/gen-nodejs/kalman_filter_types";
import { MatrixUtil, VectorUtil } from "../../util/math";
import { KalmanFilterSensorTypeUtil, SensorType } from "../../util/struct";

export const kalman_filter: KalmanFilterConfig = {
  state_vector: VectorUtil.fromArray<6>([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]), // [x, y, vx, vy, theta]
  time_step_initial: 0.1,
  state_transition_matrix: MatrixUtil.buildMatrix<6, 6>([
    [1.0, 0.0, 0.1, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.1, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
  ]),
  uncertainty_matrix: MatrixUtil.buildMatrix<6, 6>([
    [10.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    [0.0, 10.0, 0.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 2.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 2.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
  ]),
  process_noise_matrix: MatrixUtil.buildMatrix<6, 6>([
    [0.01, 0.0, 0.0, 0.0, 0.0, 0.0],
    [0.0, 0.01, 0.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.1, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.1, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.01, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.01],
  ]),
  dim_x_z: [6, 6],
  sensors: {
    [KalmanFilterSensorTypeUtil.fromEnum(SensorType.APRIL_TAG)]: {
      april_tag: {
        measurement_conversion_matrix: MatrixUtil.buildMatrix<6, 6>([
          [1, 0.0, 0.0, 0.0, 0.0, 0.0],
          [0.0, 1, 0.0, 0.0, 0.0, 0.0],
          [0.0, 0.0, 1, 0.0, 0.0, 0.0],
          [0.0, 0.0, 0.0, 1, 0.0, 0.0],
          [0.0, 0.0, 0.0, 0.0, 1, 0.0],
          [0.0, 0.0, 0.0, 0.0, 0.0, 1],
        ]),
        measurement_noise_matrix: MatrixUtil.buildMatrix<6, 6>([
          [5, 0.0, 0.0, 0.0, 0.0, 0.0],
          [0.0, 5, 0.0, 0.0, 0.0, 0.0],
          [0.0, 0.0, 1, 0.0, 0.0, 0.0],
          [0.0, 0.0, 0.0, 1, 0.0, 0.0],
          [0.0, 0.0, 0.0, 0.0, 1, 0.0],
          [0.0, 0.0, 0.0, 0.0, 0.0, 1],
        ]),
      },
    },
    [KalmanFilterSensorTypeUtil.fromEnum(SensorType.IMU)]: {
      0: {
        measurement_conversion_matrix: MatrixUtil.buildMatrix<6, 6>([
          [1, 0.0, 0.0, 0.0, 0.0, 0.0],
          [0.0, 1, 0.0, 0.0, 0.0, 0.0],
          [0.0, 0.0, 1, 0.0, 0.0, 0.0],
          [0.0, 0.0, 0.0, 1, 0.0, 0.0],
          [0.0, 0.0, 0.0, 0.0, 1, 0.0],
          [0.0, 0.0, 0.0, 0.0, 0.0, 1],
        ]),
        measurement_noise_matrix: MatrixUtil.buildMatrix<6, 6>([
          [5, 0.0, 0.0, 0.0, 0.0, 0.0],
          [0.0, 5, 0.0, 0.0, 0.0, 0.0],
          [0.0, 0.0, 0.1, 0.0, 0.0, 0.0],
          [0.0, 0.0, 0.0, 0.1, 0.0, 0.0],
          [0.0, 0.0, 0.0, 0.0, 0.01, 0.0],
          [0.0, 0.0, 0.0, 0.0, 0.0, 0.01],
        ]),
      },
    },
    [KalmanFilterSensorTypeUtil.fromEnum(SensorType.ODOM)]: {
      odom: {
        measurement_conversion_matrix: MatrixUtil.buildMatrix<6, 6>([
          [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
          [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
          [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
          [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
          [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
          [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        ]),
        measurement_noise_matrix: MatrixUtil.buildMatrix<6, 6>([
          [0.5, 0.0, 0.0, 0.0, 0.0, 0.0],
          [0.0, 0.5, 0.0, 0.0, 0.0, 0.0],
          [0.0, 0.0, 0.01, 0.0, 0.0, 0.0],
          [0.0, 0.0, 0.0, 0.01, 0.0, 0.0],
          [0.0, 0.0, 0.0, 0.0, 0.2, 0.0],
          [0.0, 0.0, 0.0, 0.0, 0.0, 0.2],
        ]),
      },
    },
  },
};
