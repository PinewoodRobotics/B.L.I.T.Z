from dataclasses import dataclass
import json
from turtle import Vec2D
from typing import List, Tuple


@dataclass
class Inference:
    confidence: float
    class_name: str
    class_id: int
    bounding_box: List[Vec2D]  # [x1, y1, x2, y2]


class Inferences(List[Inference]):
    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def from_json(cls, json_data: str) -> "Inferences":
        data = json.loads(json_data)
        inferences = cls()
        for inference_data in data:
            inferences.append(Inference(**inference_data))
        return inferences

    def to_json(self) -> str:
        return json.dumps([inf.__dict__ for inf in self], sort_keys=True, indent=4)
