import { OdomConfig } from "../../../schema/pos-extrapolator/odom-config";

export const swerve_odom_config: OdomConfig = {
  use_position: true,
  use_rotation: true,
  odom_robot_position: [0, 0, 0],
  odom_robot_rotation: [0, 0, 0],
};
