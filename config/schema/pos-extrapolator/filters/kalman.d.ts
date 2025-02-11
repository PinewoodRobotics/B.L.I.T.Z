import { Matrix } from "../../type-util/math-util";

export interface KalmanFilterSensorConfig<N extends number = 3> {
  measurement_noise_matrix: Matrix<number, N, N>;
  measurement_conversion_matrix: Matrix<number, N, N>;
  name: string;
}

export interface KalmanFilterConfig<N extends number = 3> {
  state_vector: Vector<number, N>;
  state_transition_matrix: Matrix<number, N, N>;
  uncertainty_matrix: Matrix<number, N, N>;
  process_noise_matrix: Matrix<number, N, N>;

  time_step_initial: number;

  dim_x_z: [number, number];
  sensors: Record<
    "april-tag" | "odometry" | "imu",
    KalmanFilterSensorConfig<N>
  >;
}
