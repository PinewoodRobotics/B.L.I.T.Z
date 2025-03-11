import type Config from "../schema";
import prod1 from "./cameras/prod_1";
import { home_1 } from "./tag_config/home_1";
import { buildMatrixFromArray, buildVector } from "./util/math";

const config: Config = {
  pos_extrapolator: {
    april_tag_discard_distance: 10,
    message_config: {
      post_tag_input_topic: "apriltag/tag",
      post_odometry_input_topic: "robot/odometry",
      post_imu_input_topic: "imu/imu",
      post_robot_position_output_topic: "pos-extrapolator/robot-position",
      set_position: "pos-extrapolator/set-position",
    },
    tag_position_config: home_1,
    tag_confidence_threshold: 1,
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
        [0.01, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.01, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.01, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.01, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.01],
      ]),
      dim_x_z: [5, 5],
      sensors: {
        "april-tag": {
          name: "april-tag",
          measurement_conversion_matrix: buildMatrixFromArray<number, 5, 5>([
            [1, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1],
          ]),
          measurement_noise_matrix: buildMatrixFromArray<number, 5, 5>([
            [0.5, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.5, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1000, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1000, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1],
          ]),
        },
        odometry: {
          name: "odometry",
          measurement_conversion_matrix: buildMatrixFromArray<number, 5, 5>([
            [1, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1],
          ]),
          measurement_noise_matrix: buildMatrixFromArray<number, 5, 5>([
            [0.05, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.05, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.01, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.01, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.02],
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
      prod_1: {
        camera_robot_position: buildVector<number, 3>(0.0, 0.0, 0),
        camera_robot_direction: buildVector<number, 3>(0.0, 0.0, -1.0),
        /*        camera_robot_position: buildVector<number, 3>(0.62, 0.0, 0.75),
        camera_robot_direction: buildVector<number, 3>(0.0, 0.0, -1.0),*/
      },
    },
    enable_imu: false,
    enable_odom: true,
    enable_tags: true,
  },
  autobahn: {
    host: "localhost",
    port: 8080,
  },
  cameras: [prod1],
  april_detection: {
    tag_size: 0.16,
    family: "tag36h11",
    nthreads: 2,
    quad_decimate: 1,
    quad_sigma: 0,
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
  lidar_configs: [
    {
      pi_to_run_on: "pi-1",
      port: "/dev/ttyUSB0",
      baudrate: 115200,
      is_2d: false,
      name: "lidar-1",
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
