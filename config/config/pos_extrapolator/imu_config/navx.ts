import { ImuConfig } from "../../../schema/pos-extrapolator/imu-config";

export const nav_x_config: ImuConfig = {
  use_position: true,
  use_rotation: true,
  use_velocity: true,
  imu_robot_position: [0.0, 0.0],
  imu_robot_direction_vector: [0.0, 0.0],
};
