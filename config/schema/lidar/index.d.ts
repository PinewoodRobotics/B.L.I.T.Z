import type { Vector } from "../type-util/math-util";

export interface LidarConfig {
  pi_to_run_on: string;
  port: string;
  baudrate: number;
  name: string;

  min_distance_meters: number;
  max_distance_meters: number;

  position_in_robot: Vector<number, 3>;
  rotation_in_robot: Vector<number, 3>;
}
