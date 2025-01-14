import random
import cv2
from matplotlib.pyplot import gray
import numpy as np

from config.calibration import CheckerboardConfig
from module.module_thread import ModuleThread
from module.streamer import Camera


class CameraCalibratorCheckerboard:
    def __init__(self, config: CheckerboardConfig):
        self.config = config
        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        self.image_data: dict[int, tuple[np.ndarray, np.ndarray]] = {}

        # Create object points for a single checkerboard pattern
        self.obj_3D = np.zeros((1, self.config.cols * self.config.rows, 3), np.float32)
        self.obj_3D[0, :, :2] = np.mgrid[
            0 : self.config.cols, 0 : self.config.rows
        ].T.reshape(-1, 2)
        self.obj_3D = self.obj_3D * self.config.square_size
        self.image_size = None
        # Z coordinates remain 0

    def set_image_size(self, image_size: tuple[int, int]):
        self.image_size = image_size

    def is_grid_in_image(
        self, image: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        ret, corners = cv2.findChessboardCorners(
            gray,
            (self.config.cols, self.config.rows),
            None,
            cv2.CALIB_CB_ADAPTIVE_THRESH
            + cv2.CALIB_CB_FAST_CHECK
            + cv2.CALIB_CB_NORMALIZE_IMAGE,
        )

        if ret and len(corners) == self.config.cols * self.config.rows:
            corners2 = cv2.cornerSubPix(
                gray, corners, (11, 11), (-1, -1), self.criteria
            )
            colored = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            # Draw on the color image
            cv2.drawChessboardCorners(
                colored, (self.config.cols, self.config.rows), corners2, ret
            )
            return (colored, self.obj_3D, corners2)

        # If no checkerboard found, return the color image
        return (gray, None, None)

    def add_image(self, obj_points_3D: np.ndarray, img_points_2D: np.ndarray) -> int:
        image_id = random.randint(0, 1000000)
        self.image_data[image_id] = (obj_points_3D, img_points_2D)
        return image_id

    def calibrate_camera(self):
        if len(self.image_data) < 1:
            return None

        # Extract object points and image points
        object_points = []
        image_points = []

        for obj_3D, img_2D in self.image_data.values():
            object_points.append(obj_3D)
            image_points.append(img_2D)

        # Perform camera calibration
        ret, mtx, dist_coeff, R_vecs, T_vecs = cv2.calibrateCamera(
            object_points, image_points, self.image_size, None, None  # type: ignore
        )  # type: ignore
        return mtx, dist_coeff


class CameraCalibratorCheckerboardRunner(ModuleThread):
    def __init__(self, camera: Camera, checkerboard: CameraCalibratorCheckerboard):
        super().__init__(
            target=self.run,
        )
        self.camera = camera
        self.checkerboard = checkerboard
        self.latest_result = None

    def run(self):
        self.is_running = True
        while self.is_running:
            if not self.is_running:
                return

            success, frame = self.camera.read()
            if not success:
                continue

            h, w = frame.shape[:2]
            self.checkerboard.set_image_size((1920, 1080))

            result = self.checkerboard.is_grid_in_image(frame)
            self.camera.set_frame(result[0], True)
            self.latest_result = (
                result if result[1] is not None and result[2] is not None else None
            )

    def pick_current_image(self):
        if (
            self.latest_result is None
            or self.latest_result[1] is None
            or self.latest_result[2] is None
        ):
            return None

        image_id = self.checkerboard.add_image(
            self.latest_result[1], self.latest_result[2]
        )
        return (self.latest_result[0], image_id)

    def get_matrixes(self):
        return self.checkerboard.calibrate_camera()

    def remove_image(self, image_id: int):
        self.checkerboard.image_data.pop(image_id)

    def calibrate_camera(self):
        return self.checkerboard.calibrate_camera()
