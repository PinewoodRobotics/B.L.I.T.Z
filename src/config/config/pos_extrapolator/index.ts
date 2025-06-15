import { PosExtrapolator } from "../../../blitz/generated/thrift/ts_schema/pos_extrapolator_types";
import { MatrixUtil, VectorUtil } from "../util/math";
import { MapUtil } from "../util/struct";
import { nav_x_config } from "./imu_config/navx";
import { kalman_filter } from "./kalman_filter_config";
import { message_config } from "./message_config";
import { swerve_odom_config } from "./odom_config/swerve_odom";
import { comp_lab } from "./tag_config/comp_lab";

export const pose_extrapolator: PosExtrapolator = {
  message_config: message_config,
  camera_position_config: MapUtil.fromRecord({
    one: {
      position: VectorUtil.fromArray<3>([0, 0, 0]),
      rotation: MatrixUtil.buildMatrix<3, 3>([
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
      ]),
    },
  }),
  tag_position_config: comp_lab,
  tag_confidence_threshold: 50,
  april_tag_discard_distance: 5,
  enable_imu: true,
  enable_odom: true,
  enable_tags: true,
  odom_config: swerve_odom_config,
  imu_config: nav_x_config,
  kalman_filter_config: kalman_filter,
};
