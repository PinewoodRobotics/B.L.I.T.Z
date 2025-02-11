import { Position3D } from "../type-util/position-util";
import { KalmanFilterConfig } from "./filters/kalman.d.ts";
import { ImuConfig } from "./imu-config.d.ts";
import { PosExtrapolatorMessageConfig } from "./message.d.ts";
import { OdomConfig } from "./odom-config.d.ts";

export interface PosExtrapolator {
  position_extrapolation_method:
    | "average-position"
    | "weighted-average-position"
    | "median-position"
    | "trend-line-center"
    | "kalman-linear-filter";
  message_config: PosExtrapolatorMessageConfig;
  tag_position_config: Record<string, Position3D>;
  tag_confidence_threshold: number;

  imu_configs: ImuConfig[];
  odom_configs: OdomConfig[];

  kalman_filter: KalmanFilterConfig<5>;
}
