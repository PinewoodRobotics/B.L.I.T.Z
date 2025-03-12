export interface DetectionConfig {
  image_input_topic: string;
  image_output_topic: string;
  conf_threshold: number;
  iou_threshold: number;
  batch_size: number;
}
