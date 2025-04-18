export interface PosExtrapolatorMessageConfig {
  post_tag_input_topic: string = DefaultTopics.TAG_INPUT_TOPIC;
  post_odometry_input_topic: string = DefaultTopics.ODOMETRY_INPUT_TOPIC;
  post_imu_input_topic: string = DefaultTopics.IMU_INPUT_TOPIC;

  post_robot_position_output_topic: string = DefaultTopics.ROBOT_POSITION_OUTPUT_TOPIC;

  set_position: string = DefaultTopics.SET_POSITION_OUTPUT_TOPIC;
}

export enum DefaultTopics {
  TAG_INPUT_TOPIC = "tag-input",
  ODOMETRY_INPUT_TOPIC = "odometry-input",
  IMU_INPUT_TOPIC = "imu-input",
  ROBOT_POSITION_OUTPUT_TOPIC = "robot-position-output",
  SET_POSITION_OUTPUT_TOPIC = "pos-extrapolator/set-position",
}
