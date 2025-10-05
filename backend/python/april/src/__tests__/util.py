from dataclasses import dataclass
import os
import time
import cv2
from cv2.typing import MatLike
import numpy as np
from numpy.typing import NDArray
import pyapriltags
from pydantic import BaseModel

from backend.python.april.src.camera.OV2311_camera import (
    AbstractCaptureDevice,
)
from backend.python.april.src.util import (
    get_map1_and_map2,
    get_undistored_frame,
)


def add_cur_dir(path: str):
    return os.path.join(os.path.dirname(__file__), path)


def detector():
    return pyapriltags.Detector(
        families="tag36h11",
        nthreads=1,
        quad_decimate=1.0,
    )


def tag_size():
    return 0.0254


def preprocess_image(
    image: NDArray[np.uint8] | MatLike,
    matrix: NDArray[np.float64],
    dist_coeff: NDArray[np.float64],
):
    map1, map2, new_camera_matrix = get_map1_and_map2(
        matrix, dist_coeff, image.shape[1], image.shape[0]
    )
    return get_undistored_frame(image, map1, map2), new_camera_matrix


def get_avg_fps(device: AbstractCaptureDevice):
    frame_times = []
    last_frame_time = time.time()

    for _ in range(100):
        ret, frame = device.get_frame()
        if not ret or frame is None:
            continue

        current_time = time.time()
        frame_times.append(current_time - last_frame_time)
        last_frame_time = current_time

    avg_time = sum(frame_times) / len(frame_times) if frame_times else 0

    return 1 / avg_time


class Pose(BaseModel):
    position: list[float]
    rotation_matrix: list[list[float]]


class CameraPosition(BaseModel):
    x: float
    y: float
    z: float


class Camera(BaseModel):
    position: CameraPosition
    target: str


class AprilTag(BaseModel):
    scale: float
    source_image: str


class GeneratedTagData(BaseModel):
    pose_id: int
    timestamp: float
    image_filename: str
    pose: Pose
    camera: Camera
    apriltag: AprilTag


@dataclass
class GeneratedTagDataWithImage:
    image: NDArray[np.uint8] | MatLike
    data: GeneratedTagData


def get_generated_tag_metadata(file_name: str) -> GeneratedTagData:
    with open(
        add_cur_dir(f"fixtures/images/generated_apriltags/{file_name}.json"), "r"
    ) as f:
        return GeneratedTagData.model_validate_json(f.read())


def load_png_image(file_name: str) -> NDArray[np.uint8] | MatLike:
    image = cv2.imread(
        add_cur_dir(f"fixtures/images/generated_apriltags/{file_name}.png")
    )
    assert image is not None
    return image


def get_all_generated_tags() -> list[GeneratedTagDataWithImage]:
    generated_tags = []
    for file in os.listdir(add_cur_dir("fixtures/images/generated_apriltags")):
        if not file.endswith(".png"):
            continue

        file_base = file[:-4]
        file_json_name = f"{file_base}.json"
        file_png_name = f"{file_base}.png"
        data = get_generated_tag_metadata(file_base)
        image = load_png_image(file_base)
        generated_tags.append(
            GeneratedTagDataWithImage(
                image=image,
                data=data,
            )
        )

    return generated_tags
