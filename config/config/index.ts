import type Config from "../schema";
import baseWhiteCam from "./cameras/base-white-cam";
import { home_1 } from "./tag_config/home_1";
import { buildMatrixFromArray, buildVector } from "./util/math";

const config: Config = {
  pos_extrapolator: {
    message_config: {
      post_tag_input_topic: "apriltag/tag",
      post_odometry_input_topic: "robot/odometry",
      post_imu_input_topic: "imu/imu",
      post_robot_position_output_topic: "pos-extrapolator/robot-position",
      set_position: "pos-extrapolator/set-position",
    },
    tag_position_config: home_1,
    tag_confidence_threshold: 0,
    imu_configs: {
      one: {
        use_position: true,
        use_rotation: true,
        use_velocity: true,
        imu_robot_position: [0.0, 0.0],
        imu_robot_direction_vector: [0.0, 0.0],
      },
    },
    odom_configs: {
      use_position: true,
      use_rotation: true,
      odom_robot_position: [0, 0, 0],
      odom_robot_rotation: [0, 0, 0],
    },
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
        [10.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 10.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 5.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 5.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 1.0],
      ]),
      process_noise_matrix: buildMatrixFromArray<number, 5, 5>([
        [0.1, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.1, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.1, 0.0, 0.0],
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
            [1, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1, 0.0, 0.0, 0.0],
            [0.0, 0.0, 10000.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 10000.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.2],
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
            [1, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.01, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.01, 0.0],
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
            [0.0, 0.0, 0.01, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.01, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.2],
          ]),
        },
      },
    },
    camera_configs: {
      "base-white-cam": {
        camera_robot_position: buildVector<number, 3>(0.0, 0.0, 0.1),
        camera_robot_direction: buildVector<number, 3>(0.0, 0.0, -1.0),
      },
    },
    enable_imu: false,
    enable_odom: false,
    enable_tags: true,
  },
  autobahn: {
    host: "localhost",
    port: 8080,
  },
  cameras: [baseWhiteCam],
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
