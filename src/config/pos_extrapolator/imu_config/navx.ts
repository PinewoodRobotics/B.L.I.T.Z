import { MatrixUtil, VectorUtil } from "../../util/math";

export const nav_x_config = {
  "0": {
    use_position: false,
    use_rotation: true,
    use_velocity: true,
    imu_robot_position: {
      position: VectorUtil.fromArray([0.0, 0.0, 0.0]),
      rotation: MatrixUtil.buildMatrix([
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
      ]),
    },
  },
};
