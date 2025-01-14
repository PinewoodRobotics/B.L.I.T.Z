import random
import cv2
import numpy as np
import pyapriltags
from typing import Union, Tuple, List, Dict

from config.calibration import CheckerboardConfig
from module.module_thread import ModuleThread
from module.streamer import Camera


class CameraCalibratorApriltag:
    def __init__(
        self,
        config: CheckerboardConfig,
        family: str = "tag36h11",
        nthreads: int = 1,
    ):
        self.config = config
        self.detector = pyapriltags.Detector(families=family, nthreads=nthreads)

        # Generate object points (3D real-world points for all grid corners)
        self.obj_points_list = np.zeros(
            (self.config.cols * self.config.rows * 4, 3), np.float32
        )
        index = 0
        for i in range(self.config.cols):
            for j in range(self.config.rows):
                for k in range(4):  # One object point per corner of each tag
                    self.obj_points_list[index][0] = i * self.config.square_size
                    self.obj_points_list[index][1] = j * self.config.square_size
                    index += 1

        self.img_data: Dict[int, tuple[np.ndarray, np.ndarray]] = {}

    def detect(self, image: np.ndarray) -> List[pyapriltags.Detection]:
        """Detect AprilTags in a grayscale image."""
        gray = (
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        )
        return self.detector.detect(gray)

    def is_grid_in_image(
        self, image: np.ndarray
    ) -> Tuple[np.ndarray, Union[np.ndarray, None], Union[np.ndarray, None]]:
        gray = (
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        )

        tags = self.detect(image)

        img_points = []
        for tag in tags:
            img_points.extend(tag.corners)  # Append all four corners of the tag

        if len(img_points) == self.config.cols * self.config.rows * 4:
            corners = np.array(img_points, dtype=np.float32).reshape(-1, 1, 2)

            # Ensure corners are within image bounds
            h, w = gray.shape[:2]
            mask = (
                (corners[:, 0, 0] >= 0)
                & (corners[:, 0, 0] < w)
                & (corners[:, 0, 1] >= 0)
                & (corners[:, 0, 1] < h)
            )

            if not all(mask):
                return (gray, None, None)

            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            refined_corners = cv2.cornerSubPix(
                gray,
                corners,
                (11, 11),
                (-1, -1),
                criteria,  # Also increased window size
            )

            colored = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            return (
                self.draw_apriltag_on_image(colored, tags),
                refined_corners,
                self.obj_points_list,
            )

        return (gray, None, None)

    def draw_apriltag_on_image(
        self, image: np.ndarray, tags: List[pyapriltags.Detection]
    ) -> np.ndarray:
        image_copy = image.copy()
        for tag in tags:
            # Draw the detected corners
            corners = tag.corners.astype(int)
            cv2.polylines(
                image_copy, [corners], isClosed=True, color=(0, 255, 0), thickness=2
            )

            # Draw the tag center
            center = tuple(map(int, tag.center))
            cv2.circle(image_copy, center, 5, (0, 0, 255), -1)

            # Label the tag with its ID
            cv2.putText(
                image_copy,
                f"ID: {tag.tag_id}",
                center,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                2,
            )
        return image_copy

    def add_image(
        self,
        img_points: np.ndarray,
        obj_points: np.ndarray,
    ) -> int:
        image_id = random.randint(0, 1000000)
        self.img_data[image_id] = (obj_points, img_points)
        return image_id

    def calibrate_camera(self):
        if len(self.img_data) < 1:
            raise ValueError(
                "Not enough calibration images to compute camera parameters."
            )

        # Extract object points and image points
        object_points = []
        image_points = []

        for obj_3D, img_2D in self.img_data.values():
            object_points.append(obj_3D)
            image_points.append(img_2D)

        # Get first image shape
        first_image = image_points[0]
        h, w = first_image.shape[:2]

        # Perform camera calibration
        ret, mtx, dist_coeff, R_vecs, T_vecs = cv2.calibrateCamera(
            object_points, image_points, (w, h), None, None
        )
        return mtx, dist_coeff


class CameraCalibratorApriltagRunner(ModuleThread):
    def __init__(self, camera: Camera, april_board: CameraCalibratorApriltag):
        super().__init__(target=self.run)
        self.camera = camera
        self.april_board = april_board
        self.latest_result = None

    def run(self):
        self.is_running = True
        while True:
            if not self.is_running:
                return

            success, image = self.camera.read()
            if not success:
                continue

            result = self.april_board.is_grid_in_image(image)
            self.camera.set_frame(result[0], True)
            self.latest_result = (
                result if result[1] is not None or result[2] is not None else None
            )

    def pick_current_image(self):
        if (
            self.latest_result is None
            or self.latest_result[1] is None
            or self.latest_result[2] is None
        ):
            print("No result")
            return None

        print("Picked!")

        image_id = self.april_board.add_image(
            self.latest_result[1], self.latest_result[2]
        )
        return (self.latest_result, image_id)

    def calibrate_camera(self):
        return self.april_board.calibrate_camera()

    def remove_image(self, image_id: int):
        self.april_board.img_data.pop(image_id)
