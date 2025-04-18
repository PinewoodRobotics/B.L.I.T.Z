import type { DetectionConfig } from "./detection";
import type { TrainingConfig } from "./training";

export interface MessageConfig {
  image_input_topic: string;
  inference_output_topic: string;
}

export interface ImageDetectionConfig {
  model: string;
  device: "cpu" | "gpu" | "mps";
  mode: "training" | "detection";
  training: TrainingConfig;
  detection: DetectionConfig;
  message_config: MessageConfig;
  throwaway_time_ms: number;
}
