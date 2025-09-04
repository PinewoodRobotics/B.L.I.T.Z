import { OdomConfig } from "generated/thrift/gen-nodejs/pos_extrapolator_types";
import { MatrixUtil, VectorUtil } from "../../util/math";

export const swerve_odom_config: OdomConfig = {
  use_position: true,
  use_rotation: true,
  imu_robot_position: {
    position: VectorUtil.fromArray<3>([0, 0, 0]),
    rotation: MatrixUtil.buildMatrix<3, 3>([
      [1, 0, 0],
      [0, 1, 0],
      [0, 0, 1],
    ]),
  },
};
