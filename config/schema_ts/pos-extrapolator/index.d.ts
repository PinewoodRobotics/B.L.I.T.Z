import { Position3D } from "../type-util/position-util";
import { CameraConfig } from "./camera-config.d.ts";
import { KalmanFilterConfig } from "./filters/kalman.d.ts";
import { ImuConfig } from "./imu-config.d.ts";
import { PosExtrapolatorMessageConfig } from "./message.d.ts";
import { OdomConfig } from "./odom-config.d.ts";

export interface PosExtrapolator {
  message_config: PosExtrapolatorMessageConfig;
  tag_position_config: Record<string, Position3D>;
  tag_confidence_threshold: number;
  april_tag_discard_distance: number;

  enable_imu: boolean;
  enable_odom: boolean;
  enable_tags: boolean;

  odom_configs: OdomConfig;
  imu_configs: Record<string, ImuConfig>;
  camera_configs: Record<string, CameraConfig>;

  kalman_filter: KalmanFilterConfig<5>;
}
