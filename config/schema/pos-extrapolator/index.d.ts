import { Position3D } from "../type-util/position-util";
import type { CameraConfig } from "./camera-config";
import type { KalmanFilterConfig } from "./filters/kalman";
import type { ImuConfig } from "./imu-config";
import type { PosExtrapolatorMessageConfig } from "./message";
import type { OdomConfig } from "./odom-config";

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
