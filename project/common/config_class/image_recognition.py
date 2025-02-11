from enum import Enum
from pydantic import BaseModel


class Device(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    MPS = "mps"


class Mode(str, Enum):
    TRAINING = "training"
    DETECTION = "detection"


class TrainingConfig(BaseModel):
    imgsz: int
    epochs: int
    batch_size: int


class DetectionConfig(BaseModel):
    image_input_topic: str
    image_output_topic: str


class ImageRecognitionConfig(BaseModel):
    model: str
    device: Device
    mode: Mode
    training: TrainingConfig
    detection: DetectionConfig
