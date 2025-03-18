import type Config from "../schema";
import { april_tag_detection_config } from "./april_tags_detection";
import { autobahn_config } from "./autobahn";
import prod1 from "./cameras/prod_1";
import { pose_extrapolator } from "./pos_extrapolator";
import { buildVector } from "./util/math";

const config: Config = {
  pos_extrapolator: pose_extrapolator,
  autobahn: autobahn_config,
  cameras: [prod1],
  april_detection: april_tag_detection_config,
  logger: {
    enabled: false,
    profiler: {
      activated: false,
      profile_functions: false,
      time_functions: false,
      output_file: "profiler.json",
    },
    level: "DEBUG",
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
  lidar_configs: [
    {
      pi_to_run_on: "pi-1",
      port: "/dev/ttyUSB0",
      baudrate: 115200,
      name: "lidar-1",
      is_2d: false,
      min_distance_meters: 0.1,
      max_distance_meters: 10.0,
      position_in_robot: buildVector<number, 3>(0.0, 0.0, 0.0),
      rotation_in_robot: buildVector<number, 3>(0.0, 0.0, 0.0),
    },
  ],
  watchdog: {
    send_stats: true,
    stats_interval_seconds: 1,
    stats_publish_topic: "stats/publish",
  },
};

export default config;
