import { AprilDetectionConfig } from "./apriltag";
import { AutobahnConfig } from "./autobahn";
import { CameraParameters } from "./camera";
import { ImageDetectionConfig } from "./image-recognition";
import { LoggerConfig } from "./logging/logger";
import { PosExtrapolator } from "./pos-extrapolator";

export default interface Config {
  autobahn: AutobahnConfig;
  pos_extrapolator: PosExtrapolator;
  image_recognition: ImageDetectionConfig;
  cameras: CameraParameters[];
  april_detection: AprilDetectionConfig;
  logger: LoggerConfig;
}
