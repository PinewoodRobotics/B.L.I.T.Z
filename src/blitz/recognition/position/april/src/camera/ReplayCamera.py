from cscore import CvSource, CvSink, VideoMode
import cv2
import numpy as np
import threading
import time

from blitz.common.debug.replay_recorder import get_next_replay
from blitz.recognition.position.april.src.camera.abstract_camera import (
    AbstractCaptureDevice,
    CameraType,
)


class ReplaySink(CvSink):
    def __init__(self, name: str, sleep_time: float):
        super().__init__(name)
        self.sleep_time = sleep_time

    def grabFrame(
        self, image: np.ndarray, timeout: float = 0.225
    ) -> tuple[int, np.ndarray]:
        replay = get_next_replay()
        if replay is None:
            return 0, image

        if replay.data_type == "ndarray":
            image = np.frombuffer(replay.data, dtype=np.uint8).reshape((1, 1, 3))

        return 1, image


class ReplayCamera(AbstractCaptureDevice, type=CameraType.VIDEO_FILE):
    def __init__(
        self,
        video_file_path: str,
        width: int = 1280,
        height: int = 720,
        max_fps: float = 30,
    ):
        self.video_file_path = video_file_path
        self.cv_cap = cv2.VideoCapture(self.video_file_path)

        # Get actual video dimensions if possible
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
