from pydantic import BaseModel


class TrainerConfig(BaseModel):
    name: str
    imgsz: int
    epochs: int
    data_yaml_path: str
    dataset_root_path: str
    batch_size: int


class ImageRecognitionConfig(BaseModel):
    image_input_topic: str
    image_output_topic: str
    model: str
    device: str
    trainer: TrainerConfig
