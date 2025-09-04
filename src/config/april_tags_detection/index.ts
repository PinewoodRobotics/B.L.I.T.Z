import { AprilDetectionConfig } from "generated/thrift/gen-nodejs/apriltag_types";

export const april_tag_detection_config: AprilDetectionConfig = {
  tag_size: 0.17,
  family: "tag36h11",
  nthreads: 4,
  quad_decimate: 1,
  quad_sigma: 0,
  refine_edges: true,
  decode_sharpening: 0.25,
  searchpath: ["apriltags"],
  debug: false,
  message: {
    post_camera_output_topic: "apriltag/camera",
    post_tag_output_topic: "apriltag/tag",
  },
  send_stats: true,
  stats_topic: "apriltag/stats",
};
