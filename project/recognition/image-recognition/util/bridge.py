
import numpy as np
from ultralytics import YOLO
from ultralytics.engine.results import Results

from generated.Inference_pb2 import Inference, InferenceList
from project.common.config_class.image_recognition import ImageRecognitionConfig

class ImageRecognition:
    def __init__(self, config: ImageRecognitionConfig):
        self.config = config
        self.model = YOLO(config.model)
        self.model.to(config.device)
        self.conf_threshold = config.detection.conf_threshold
        self.iou_threshold = config.detection.iou_threshold
    
    def predict(self, np_image: np.ndarray, name: str, image_id: int) -> InferenceList:
        results = self.model(np_image, conf=self.conf_threshold, iou=self.iou_threshold)
        return InferenceList(
            camera_name=name, 
            image_id=image_id,
            inferences=[Inference(
                confidence=result.conf[0].item(),
                class_name=result.names[int(result.cls[0].item())],
                class_id=int(result.cls[0].item()),
                bounding_box=result.xyxy[0].tolist()
            ) for result in results]
        )
    
    async def predict_batch(self, images: list[np.ndarray]) -> list[InferenceList]:
        results = self.model(images, conf=self.conf_threshold, iou=self.iou_threshold)
        return [self._process_result(result) for result in results]
    
    def _process_result(self, result: Results) -> InferenceList:
        if result.boxes is None:
            return InferenceList(inferences=[])
        
        inferences = []
        for i in range(len(result.boxes)):
            inferences.append(Inference(
                confidence=result.boxes[i].conf.item(),
                class_name=result.names[int(result.boxes[i].cls.item())],
                class_id=int(result.boxes[i].cls.item()),
                bounding_box=result.boxes[i].xyxy[0].tolist()
            ))
            
        return InferenceList(inferences=inferences)
    
    async def warmup(self, shape=(640, 640)):
        dummy_input = np.zeros((*shape, 3), dtype=np.uint8)
        self.predict(dummy_input, "warmup", -1)
