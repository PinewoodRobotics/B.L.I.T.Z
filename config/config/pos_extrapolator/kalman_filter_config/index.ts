import type { KalmanFilterConfig } from "../../../../generated/thrift/ts_schema/kalman_filter_types";
import { MatrixUtil, VectorUtil } from "../../util/math";
import {
  KalmanFilterSensorTypeUtil,
  MapUtil,
  SensorType,
} from "../../util/struct";

export const kalman_filter: KalmanFilterConfig = {
  state_vector: VectorUtil.fromArray<6>([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]), // [x, y, vx, vy, theta]
  time_step_initial: 0.1,
  state_transition_matrix: MatrixUtil.buildMatrix<6, 6>([
    [1.0, 0.0, 0.1, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.1, 0.0],
    [0.0, 0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 1.0],
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
  dim_x_z: [5, 5],
  sensors: MapUtil.fromRecord({
    [KalmanFilterSensorTypeUtil.fromEnum(SensorType.APRIL_TAG)]:
      MapUtil.fromRecord({
        config: {
          name: "april-tag",
          measurement_conversion_matrix: MatrixUtil.buildMatrix<6, 6>([
            [1, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 1],
          ]),
          measurement_noise_matrix: MatrixUtil.buildMatrix<6, 6>([
            [0.5, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.5, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1000, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1000, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1000, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 1000],
          ]),
        },
      }),
    [KalmanFilterSensorTypeUtil.fromEnum(SensorType.APRIL_TAG)]:
      MapUtil.fromRecord({
        config: {
          name: "odometry",
          measurement_conversion_matrix: MatrixUtil.buildMatrix<6, 6>([
            [1, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 1],
          ]),
          measurement_noise_matrix: MatrixUtil.buildMatrix<6, 6>([
            [0.05, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.05, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.01, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.01, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.02, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.02],
          ]),
        },
      }),
    [KalmanFilterSensorTypeUtil.fromEnum(SensorType.APRIL_TAG)]:
      MapUtil.fromRecord({
        config: {
          name: "imu",
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
      }),
  }),
};
