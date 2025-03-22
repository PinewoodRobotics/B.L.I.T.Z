import { PosExtrapolator } from "../../schema/pos-extrapolator";
import { physics_room } from "../tag_config/physics_room";
import { buildVector } from "../util/math";
import { nav_x_config } from "./imu_config/navx";
import { kalman_filter } from "./kalman_filter_config";
import { message_config } from "./message_config";
import { swerve_odom_config } from "./odom_config/swerve_odom";

export const pose_extrapolator: PosExtrapolator = {
  april_tag_discard_distance: 1000,
  tag_confidence_threshold: 1,
  enable_imu: false,
  enable_odom: false,
  enable_tags: true,

  tag_position_config: physics_room,
  message_config: message_config,
  kalman_filter: kalman_filter,
  imu_configs: {
    navx: nav_x_config,
  },
  odom_configs: swerve_odom_config,
  camera_configs: {
    front_right: {
      camera_robot_position: buildVector<number, 3>(
        (Math.sqrt(2) / 2) * 0.2,
        (-Math.sqrt(2) / 2) * 0.2,
        0
      ),
      camera_robot_direction: buildVector<number, 3>(
        Math.sqrt(2) / 2,
        -Math.sqrt(2) / 2,
        0
      ),
    },
  },
};
