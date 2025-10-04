from typing import SupportsFloat, override
from cscore import CvSource, CvSink, VideoMode
import cv2
import numpy as np
import threading
import time

from numpy.typing import NDArray

from backend.generated.thrift.config.camera.ttypes import CameraType
from backend.python.april.src.camera.abstract_camera import AbstractCaptureDevice
from backend.python.common.camera.image_utils import from_proto_image
from backend.python.common.debug.logger import error
from backend.python.common.debug.replay_recorder import get_next_key_replay


class ReplaySink(CvSink):
    def __init__(self, name: str, camera_topic: str):
        super().__init__(name)
        self.camera_topic = camera_topic

    @override
    def grabFrame(
        self, image: NDArray[np.uint8], timeout: SupportsFloat = 0.225
    ) -> tuple[int, NDArray[np.uint8]]:
        replay = get_next_key_replay(self.camera_topic)
        if replay is None:
            error(f"No replay found for camera topic: {self.camera_topic}")
            return 0, image

        image = from_proto_image(replay.data)

        return 1, image


class ReplayCamera(AbstractCaptureDevice, type=CameraType.VIDEO_FILE):
    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        camera_topic: str = "camera",
        max_fps: float = 30,
        camera_matrix: NDArray[np.float64] = np.eye(3),
        dist_coeff: NDArray[np.float64] = np.zeros(5),
    ):
        super().__init__(
            camera_port=camera_topic,
            width=width,
            height=height,
            max_fps=max_fps,
            camera_matrix=camera_matrix,
            dist_coeff=dist_coeff,
        )

        self.sink = ReplaySink(camera_topic, camera_topic)

    def _initialize_camera(self):
        self._is_ready = True


class ReplayCameraCV(AbstractCaptureDevice, type=CameraType.VIDEO_FILE):
    def __init__(
        self,
        video_file_path: str,
        width: int = 1280,
        height: int = 720,
        max_fps: float = 30,
    ):
        self.video_file_path = video_file_path
        self.cv_cap = cv2.VideoCapture(self.video_file_path)

        if self.cv_cap.isOpened():
            width = int(self.cv_cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or width
            height = int(self.cv_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or height
            video_fps = self.cv_cap.get(cv2.CAP_PROP_FPS) or max_fps
            max_fps = min(max_fps, video_fps)

        super().__init__(
            camera_port=video_file_path,
            width=width,
            height=height,
            max_fps=max_fps,
            camera_matrix=np.eye(3),
            dist_coeff=np.zeros(5),
        )

        self._stop_thread = False
        self._thread = None

    def _configure_camera(self):
        # Create CvSource to act as the camera source for cscore
        self.camera = CvSource(
            "VIDEO_FILE",
            VideoMode.PixelFormat.kBGR,
            self.width,
            self.height,
            int(self.max_fps),
        )
        self.sink = CvSink("VIDEO_FILE_SINK")
        self.sink.setSource(self.camera)

        # Start thread to feed frames from video file to CvSource
        self._start_video_thread()

    def _start_video_thread(self):
        """Start background thread to read video file and feed frames to CvSource"""

        def video_feeder():
            frame_interval = 1.0 / self.max_fps

            while not self._stop_thread and self.cv_cap.isOpened():
                ret, frame = self.cv_cap.read()
                if not ret:
                    # Loop video or stop
                    self.cv_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                # Resize frame if needed
                if frame.shape[:2] != (self.height, self.width):
                    frame = cv2.resize(frame, (self.width, self.height))

                # Put frame to CvSource
                assert isinstance(self.camera, CvSource)
                self.camera.putFrame(frame)

                time.sleep(frame_interval)

        self._thread = threading.Thread(target=video_feeder, daemon=True)
        self._thread.start()

    def release(self):
        """Override release to stop video thread and cleanup"""
        self._stop_thread = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        if self.cv_cap:
            self.cv_cap.release()

        super().release()
