import { PosExtrapolatorMessageConfig } from "generated/thrift/gen-nodejs/pos_extrapolator_types";

export const message_config: PosExtrapolatorMessageConfig = {
  post_tag_input_topic: "apriltag/tag",
  post_odometry_input_topic: "robot/odometry",
  post_imu_input_topic: "imu/imu",
  post_robot_position_output_topic: "pos-extrapolator/robot-position",
};
