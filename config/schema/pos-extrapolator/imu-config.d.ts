import { Matrix } from "../type-util/math-util";

export interface ImuConfig {
  imu_global_position: Matrix<number, 2, 1>;
  imu_local_position: Matrix<number, 2, 1>;

  imu_yaw_offset: number;
  max_r2_drift: number;
}
