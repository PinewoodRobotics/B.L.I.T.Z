from enum import Enum
from pydantic import BaseModel


class Device(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    MPS = "mps"


class Mode(str, Enum):
    TRAINING = "training"
    DETECTION = "detection"


class MessageConfig(BaseModel):
    image_input_topic: str
    inference_output_topic: str

class TrainingConfig(BaseModel):
    imgsz: int
    epochs: int
    batch_size: int


class DetectionConfig(BaseModel):
    image_input_topic: str
    image_output_topic: str
    
    conf_threshold: float = 0.25  # Default confidence threshold
    iou_threshold: float = 0.45   # Default IOU threshold
    batch_size: int = 1           # Default batch size


class ImageRecognitionConfig(BaseModel):
    model: str
    device: Device
    mode: Mode
    training: TrainingConfig
    detection: DetectionConfig
    throwaway_time_ms: int = 250
    
    message_config: MessageConfig
