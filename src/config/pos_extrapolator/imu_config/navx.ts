import { MatrixUtil, VectorUtil } from "../../util/math";

export const nav_x_config = {
  "0": {
    use_position: false,
    use_rotation: false,
    use_velocity: true,
    imu_robot_position: {
      position: VectorUtil.fromArray<3>([0.0, 0.0, 0.0]),
      rotation: MatrixUtil.buildMatrix<3, 3>([
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
      ]),
    },
  },
};
