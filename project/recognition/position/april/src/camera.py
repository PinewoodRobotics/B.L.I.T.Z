import cv2
import numpy as np
from project.common.camera.transform import unfisheye_image
from project.common.config_class.camera_parameters import (
    CameraParameters,
    CameraParametersConfig,
)


## TODO: add a config for removing colors.
class Camera:
    def __init__(self, config: CameraParameters):
        self.config = config
        self.video_capture = cv2.VideoCapture(self.config.port, cv2.CAP_AVFOUNDATION)

        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.video_capture.set(cv2.CAP_PROP_FPS, 100)

        self.cur_frame = 0

    def read(self) -> tuple[bool, cv2.typing.MatLike]:
        return self.video_capture.read()

    def release(self):
        self.video_capture.release()

    def get_matrix(self) -> np.ndarray:
        return self.config.get_np_camera_matrix()

    def get_dist_coeff(self) -> np.ndarray:
        return self.config.get_np_dist_coeff()

    def read_with_exclusions_gray(self, min_color: int, max_color: int):
        got, frame = self.read()
        if not got:
            return None, None

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
        new_frame = np.where(
            (gray_frame > min_color) & (gray_frame < max_color), 255, 0
        ).astype(
            np.uint8
        )  # Apply threshold

        return got, new_frame

    def read_with_cropping(self, min_color: np.ndarray, max_color: np.ndarray):
        got, frame = self.read()
        if not got:
            return None, None, None

        unfisheye, new_mtrx = unfisheye_image(
            frame,
            np.array(self.config.camera_matrix),
            np.array(self.config.dist_coeff),
        )

        # Create mask for the tag color range
        tag_mask = cv2.inRange(unfisheye, min_color, max_color)

        # Create white background
        result = np.full_like(tag_mask, 255, dtype=np.uint8)

        # Set masked areas to black (0)
        result[tag_mask > 0] = 0

        return got, result, new_mtrx
