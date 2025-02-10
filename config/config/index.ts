import type Config from "../schema";
import { buildMatrixFromArray, buildVector } from "./util/math";

const config: Config = {
  pos_extrapolator: {
    position_extrapolation_method: "average-position",
    message_config: {
      post_tag_input_topic: "tag-input",
      post_odometry_input_topic: "",
      post_imu_input_topic: "",
      post_robot_position_output_topic: "",
    },
    tag_position_config: {
      "tag-1": {
        x: 0,
        y: 0,
        z: 0,
        direction_vector: buildVector<number, 3>(0, 0, 1),
      },
    },
    tag_confidence_threshold: 0,
    imu_configs: [],
    odom_configs: [],
    kalman_filter: {
      state_vector: buildVector<number, 3>(0.0, 0.0, 0.0),
      time_step_initial: 0,
      state_transition_matrix: buildMatrixFromArray<number, 3, 3>([
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
      ]),
      uncertainty_matrix: buildMatrixFromArray<number, 3, 3>([
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
      ]),
      process_noise_matrix: buildMatrixFromArray<number, 3, 3>([
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
      ]),
      dim_x_z: [3, 1],
      sensors: {
        "april-tag": [],
        odometry: [],
        imu: [],
      },
    },
  },
  autobahn: {
    host: "localhost",
    port: 8080,
  },
  cameras: [],
  april_detection: {
    tag_size: 0,
    family: "",
    nthreads: 0,
    quad_decimate: 0,
    quad_sigma: 0,
    refine_edges: false,
    decode_sharpening: 0,
    searchpath: "",
    debug: false,
    message: {
      post_camera_output_topic: "",
      post_tag_output_topic: "",
    },
  },
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
    },
  },
};

export default config;
