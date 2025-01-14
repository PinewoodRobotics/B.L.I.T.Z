export interface Range {
  min: number;
  max: number;
}

export interface CameraCalibration {
  undistort: boolean;
  camera_matrix: number[][];
  dist_coeff: number[];
}

export interface Threshholding {
  hue: Range;
  saturation: Range;
  value: Range;
}

export interface CameraSettings {
  exposure: Range;
  gain: Range;
  gamma: Range;
}

export interface Filtering {
  object_size: Range;
  bounding_box_aspect_ratio: Range;
  fullness: Range;
}

export interface AprilTagConfig {
  quad_decimate: number;
  quad_sigma: number;
  refine_edges: number;
  decode_sharpening: number;
  tag_size_m: number;
}

export interface TransformationConfig {
  detect_april_tags: boolean;
  use_grayscale: boolean;
  undistort: Partial<CameraCalibration>;
  camera_settings: Partial<CameraSettings>;
  threshholding: Partial<Threshholding>;
  filtering: Partial<Filtering>;
  april_tag_config: Partial<AprilTagConfig>;
}
