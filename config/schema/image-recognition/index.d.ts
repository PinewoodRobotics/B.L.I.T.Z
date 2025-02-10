import type { DetectionConfig } from "./detection";
import type { TrainingConfig } from "./training";

export interface ImageDetectionConfig {
  model: string;
  device: "cpu" | "gpu" | "mps";
  mode: "training" | "detection";
  training: TrainingConfig;
  detection: DetectionConfig;
}
