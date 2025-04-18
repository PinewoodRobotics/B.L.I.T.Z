import { type Vector } from "../type-util/math-util";

export interface ImuConfig {
  use_rotation: boolean;
  use_position: boolean;
  use_velocity: boolean;

  imu_robot_position: Vector<number, 2>;
  imu_robot_direction_vector: Vector<number, 2>;
}
