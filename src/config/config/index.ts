import type { Config } from "../../blitz/generated/thrift/gen-nodejs/config_types";
import { april_tag_detection_config } from "./april_tags_detection";
import { autobahn_config } from "./autobahn";
import prod1 from "./cameras/prod_1";
import lidar_configs from "./lidar";
import { pose_extrapolator } from "./pos_extrapolator";
import { LogLevel, LogLevelUtil } from "./util/struct";

const config: Config = {
  pos_extrapolator: pose_extrapolator,
  autobahn: autobahn_config,
  cameras: [prod1],
  april_detection: april_tag_detection_config,
  logger: {
    enabled: false,
    level: LogLevelUtil.fromEnum(LogLevel.DEBUG),
    profiler: {
      activated: true,
      profile_functions: true,
      time_functions: true,
      output_file: "profiler.json",
    },
  },
  image_recognition: {
    model: "",
    device: "cpu",
    mode: "detection",
    training: {
      imgsz: 0,
      epochs: 0,
      batch_size: 0,
    },
    detection: {
      image_input_topic: "",
      image_output_topic: "",
      conf_threshold: 0,
      iou_threshold: 0,
      batch_size: 0,
    },
    message_config: {
      image_input_topic: "",
      inference_output_topic: "",
    },
    throwaway_time_ms: 0,
  },
  watchdog: {
    send_stats: true,
    stats_interval_seconds: 1,
    stats_publish_topic: "stats/publish",
    confirmation_topic: "",
  },
  lidar_configs: lidar_configs,
};

export default config;
