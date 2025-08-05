include "../common/common.thrift"
include "./kalman_filter.thrift"

namespace py config.pos_extrapolator

struct PosExtrapolatorMessageConfig {
    1: required string post_tag_input_topic,
    2: required string post_odometry_input_topic,
    3: required string post_imu_input_topic,
    4: required string post_robot_position_output_topic,
}

struct OdomConfig {
    1: required bool use_position,
    2: required bool use_rotation,
    3: required common.Point3 imu_robot_position,
}

struct ImuConfig {
    1: required bool use_rotation,
    2: required bool use_position,
    3: required bool use_velocity,
    4: required common.Point3 imu_robot_position,
}

struct PosExtrapolator {
    1: required PosExtrapolatorMessageConfig message_config,
    2: required map<i32, common.Point3> tag_position_config,
    3: required double tag_confidence_threshold,
    4: required double april_tag_discard_distance,
    5: required bool enable_imu,
    6: required bool enable_odom,
    7: required bool enable_tags,
    8: required OdomConfig odom_config,
    9: required map<string, ImuConfig> imu_config,
    10: required kalman_filter.KalmanFilterConfig kalman_filter_config,
    11: required map<string, common.Point3> camera_position_config,
    12: optional double time_s_between_position_sends,
    13: optional string composite_publish_topic,
    14: required bool tag_use_imu_rotation
}