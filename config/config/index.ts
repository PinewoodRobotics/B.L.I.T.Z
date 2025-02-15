import type Config from "../schema";
import large640480 from "./cameras/large-640-480";
import { buildMatrixFromArray, buildVector } from "./util/math";

const config: Config = {
  pos_extrapolator: {
    position_extrapolation_method: "kalman-linear-filter",
    message_config: {
      post_tag_input_topic: "apriltag/tag",
      post_odometry_input_topic: "robot/odometry",
      post_imu_input_topic: "imu/imu",
      post_robot_position_output_topic: "pos-extrapolator/robot-position",
      set_position: "pos-extrapolator/set-position",
    },
    tag_position_config: {
      "11": {
        x: -0.28758490410570503,
        y: 0.4010309507355102,
        z: 2.171314532618703,
        direction_vector: [
          0.10165828535398637, 0.06647378710491299, -0.9925835234875711,
        ],
      },
    },
    tag_confidence_threshold: 0,
    imu_configs: [],
    odom_configs: [
      {
        name: "odometry",
        odom_global_position: [0.0, 0.0],
        odom_local_position: [0.0, 0.0],
        odom_yaw_offset: 0,
        max_r2_drift: 0,
      },
    ],
    kalman_filter: {
      state_vector: buildVector<number, 5>(0.0, 0.0, 0.0, 0.0, 0.0), // [x, y, vx, vy, theta]
      time_step_initial: 0.1,
      state_transition_matrix: buildMatrixFromArray<number, 5, 5>([
        [1.0, 0.0, 0.1, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.1, 0.0],
        [0.0, 0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 1.0],
      ]),
      uncertainty_matrix: buildMatrixFromArray<number, 5, 5>([
        [100.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 100.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 100.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 100.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 10.0],
      ]),
      process_noise_matrix: buildMatrixFromArray<number, 5, 5>([
        [1.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.1, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.1],
      ]),
      dim_x_z: [5, 5],
      sensors: {
        "april-tag": {
          name: "april-tag",
          measurement_conversion_matrix: buildMatrixFromArray<number, 5, 5>([
            [1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0],
          ]),
          measurement_noise_matrix: buildMatrixFromArray<number, 5, 5>([
            [10.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 10.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 10.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 10.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0],
          ]),
        },
        odometry: {
          name: "odometry",
          measurement_conversion_matrix: buildMatrixFromArray<number, 5, 5>([
            [1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0],
          ]),
          measurement_noise_matrix: buildMatrixFromArray<number, 5, 5>([
            [0.5, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.5, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.2, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.2, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.5],
          ]),
        },
        imu: {
          name: "imu",
          measurement_conversion_matrix: buildMatrixFromArray<number, 5, 5>([
            [1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0],
          ]),
          measurement_noise_matrix: buildMatrixFromArray<number, 5, 5>([
            [0.5, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.5, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.5, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.2, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.2],
          ]),
        },
      },
    },
  },
  autobahn: {
    host: "localhost",
    port: 8080,
  },
  cameras: [large640480],
  april_detection: {
    tag_size: 0.2,
    family: "tag36h11",
    nthreads: 8,
    quad_decimate: 1.0,
    quad_sigma: 0.0,
    refine_edges: true,
    decode_sharpening: 0.25,
    searchpath: "apriltags",
    debug: false,
    message: {
      post_camera_output_topic: "apriltag/camera",
      post_tag_output_topic: "apriltag/tag",
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
