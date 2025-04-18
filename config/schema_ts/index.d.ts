import { AprilDetectionConfig } from "./apriltag";
import { AutobahnConfig } from "./autobahn";
import { CameraParameters } from "./camera";
import { ImageDetectionConfig } from "./image-recognition";
import { LidarConfig } from "./lidar";
import { LoggerConfig } from "./logging/logger";
import { PosExtrapolator } from "./pos-extrapolator";
import { WatchdogConfig } from "./watchdog";

export default interface Config {
  autobahn: AutobahnConfig;
  watchdog: WatchdogConfig;
  pos_extrapolator: PosExtrapolator;
  image_recognition: ImageDetectionConfig;
  cameras: CameraParameters[];
  lidar_configs: LidarConfig[];
  april_detection: AprilDetectionConfig;
  logger: LoggerConfig;
}
