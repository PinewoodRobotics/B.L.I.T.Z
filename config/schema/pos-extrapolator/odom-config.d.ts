import { type Vector } from "../type-util/math-util";

export interface OdomConfig {
  name: string;
  odom_global_position: Vector<number, 2, 1>;
  odom_local_position: Vector<number, 2, 1>;

  odom_yaw_offset: number;
  max_r2_drift: number;
}
