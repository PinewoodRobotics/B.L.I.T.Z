import { LidarConfig } from "../../generated_schema/lidar_types";
import { MatrixUtil, VectorUtil } from "../util/math";
import { MapUtil } from "../util/struct";

const lidar_configs: Map<string, LidarConfig> = MapUtil.fromRecord({
  "lidar-1": {
    pi_to_run_on: "pi-1",
    port: "/dev/ttyUSB0",
    baudrate: 115200,
    name: "lidar-1",
    is_2d: false,
    min_distance_meters: 0.1,
    max_distance_meters: 10.0,
    position_in_robot: VectorUtil.fromArray<3>([0.0, 0.0, 0.0]),
    rotation_in_robot: MatrixUtil.buildMatrix<3, 3>([
      [1, 0, 0],
      [0, 1, 0],
      [0, 0, 1],
    ]),
  },
});

export default lidar_configs;
