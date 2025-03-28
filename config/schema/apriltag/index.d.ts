export interface AprilDetectionMessageConfig {
  post_camera_output_topic: string;
  post_tag_output_topic: string;
}

export interface AprilDetectionConfig {
  tag_size: number;
  family: string;
  nthreads: number;
  quad_decimate: number;
  quad_sigma: number;
  refine_edges: boolean;
  decode_sharpening: number;
  searchpath: string;
  debug: boolean;
  message: AprilDetectionMessageConfig;

  send_stats: boolean;
  stats_topic: string;
}
