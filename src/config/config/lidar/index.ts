import { LidarConfig } from "../../../blitz/generated/thrift/gen-nodejs/lidar_types";
import { MatrixUtil, VectorUtil } from "../util/math";

const lidar_configs: {
  [k: string]: LidarConfig;
} = {
  "lidar-1": {
    pi_to_run_on: "tripoli",
    port: "/dev/ttyUSB0",
    baudrate: 2000000,
    is_2d: false,
    min_distance_meters: 0,
    max_distance_meters: 40.0,
    cloud_scan_num: 28,
    position_in_robot: VectorUtil.fromArray<3>([0.0, 0.0, 0.0]),
    rotation_in_robot: MatrixUtil.buildMatrix<3, 3>([
      [1, 0, 0],
      [0, 1, 0],
      [0, 0, 1],
    ]),
  },
};

export default lidar_configs;
