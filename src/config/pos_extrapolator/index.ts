import {
  PosExtrapolator,
  TagUseImuRotation,
} from "generated/thrift/gen-nodejs/pos_extrapolator_types";
import { MatrixUtil, VectorUtil } from "../util/math";
import { nav_x_config } from "./imu_config/navx";
import { kalman_filter } from "./kalman_filter_config";
import { message_config } from "./message_config";
import { swerve_odom_config } from "./odom_config/swerve_odom";
import { reefscape_field } from "./tag_config/reefscape";

export const pose_extrapolator: PosExtrapolator = {
  message_config: message_config,
  camera_position_config: {
    prod_1: {
      position: VectorUtil.fromArray([0, 0, 0]),
      rotation: MatrixUtil.buildMatrix([
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
      ]),
    },
  },
  tag_position_config: reefscape_field,
  tag_confidence_threshold: 50,
  april_tag_discard_distance: 5,
  tag_use_imu_rotation: TagUseImuRotation.UNTIL_FIRST_NON_TAG_ROTATION,
  enable_imu: true,
  enable_odom: false,
  enable_tags: true,
  odom_config: swerve_odom_config,
  imu_config: nav_x_config,
  kalman_filter_config: kalman_filter,
  time_s_between_position_sends: 0.025,
};
