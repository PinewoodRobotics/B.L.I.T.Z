from dataclasses import dataclass
import json
import os
import random
from typing import Dict, List, Optional

import cv2
import numpy as np


@dataclass
class TTagMetadata:
    side_size_cm: float
    depth_m: float
    left_bottom: Dict[str, float]
    center: Dict[str, float]
    pixel_corners: List[List[float]]


@dataclass
class TDetectionMetadata:
    metadata: Optional[Dict[int, TTagMetadata]] = None
    all: Optional[List[int]] = None


@dataclass
class TImageMetadata:
    tags: Optional[TDetectionMetadata] = None
    camera_matrix: Optional[List[float]] = None
    dist_coeff: Optional[List[float]] = None


class TFile:
    def __init__(self, path: str):
        self.is_image = path.endswith(".png") or path.endswith(".jpg")

        if self.is_image:
            self.cv2_image = cv2.imread(path)
        else:
            self.cv2_image = None

        self.path = path
        self.has_corresponding_annotation = False
        self.annotation_path: Optional[str] = None

    def get_annotation(self) -> TImageMetadata:
        if not self.has_corresponding_annotation:
            raise ValueError("No corresponding annotation found")

        if self.annotation_path is None:
            raise ValueError("No annotation path found")

        return TImageMetadata(**json.load(open(self.annotation_path)))

    def get_image(self):
        if not self.is_image:
            raise ValueError("Not an image")

        return self.cv2_image

    def __str__(self):
        return f"{self.path} {self.has_corresponding_annotation}"


class TImageStore:
    def __init__(self, root_image_dir: str = "store/images/"):
        self.all_files_and_subfiles: List[TFile] = []
        self.all_dirs: List[str] = []
        self.root_image_dir = root_image_dir
        self._scan_files()

    def _scan_files(self):
        for root, dirs, files in os.walk(self.root_image_dir):
            for dir in dirs:
                self.all_dirs.append(os.path.join(root, dir))
            for file in files:
                self.all_files_and_subfiles.append(TFile(os.path.join(root, file)))

        count = 0
        while count < len(self.all_files_and_subfiles):
            file = self.all_files_and_subfiles[count]
            if file.is_image:
                image_name = os.path.splitext(os.path.basename(file.path))[0]
                for annotation_file in self.all_files_and_subfiles:
                    if annotation_file.is_image:
                        continue

                    annotation_name = os.path.splitext(
                        os.path.basename(annotation_file.path)
                    )[0]
                    if image_name == annotation_name:
                        file.has_corresponding_annotation = True
                        file.annotation_path = annotation_file.path
                        self.all_files_and_subfiles.pop(count)
                        count -= 1
                        break

            count += 1

    def random_image_with_metadata(self):
        return random.choice(
            [
                f
                for f in self.all_files_and_subfiles
                if f.is_image and f.has_corresponding_annotation
            ]
        )

    def random_image(self):
        return random.choice([f for f in self.all_files_and_subfiles if f.is_image])
