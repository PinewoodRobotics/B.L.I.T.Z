import { type Vector } from "../type-util/math-util";

export interface OdomConfig {
  use_position: boolean;
  use_rotation: boolean;

  odom_robot_position: Vector<number, 3>;
  odom_robot_rotation: Vector<number, 3>;
}
