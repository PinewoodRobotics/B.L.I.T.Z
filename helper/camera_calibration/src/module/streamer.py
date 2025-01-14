import cv2
import numpy as np
import websockets
import asyncio
import pyapriltags
from config.transformation import TransformationConfig
from util.camera import apply_all_transformations


class Camera:
    def __init__(self, camera_port: int):
        self.camera = cv2.VideoCapture(camera_port)
        self.frame: np.ndarray | None = None
        self.success: bool = False
        self._set_frame_lock = False

    def read(self) -> tuple[bool, np.ndarray]:
        success, frame = self.camera.read()
        if not self._set_frame_lock:
            self.success, self.frame = success, frame
        return success, frame

    def set_frame(self, frame: np.ndarray, success: bool = True):
        self.frame = frame
        self.success = success

    def set_frame_lock(self, state: bool):
        self._set_frame_lock = state

    def read_local(self) -> tuple[bool, np.ndarray | None]:
        if self._set_frame_lock:
            return self.success, self.frame
        return self.camera.read()


class Streamer:
    def __init__(
        self,
        ws_listen_port: int,
        camera: Camera,
        transformation_config: TransformationConfig,
        detector: pyapriltags.Detector,
    ):
        self.ws_listen_port = ws_listen_port
        self.ws_server = None
        self.camera = camera
        self.no_read_mode = False
        self.active_connections = set()  # Track active connections
        self.transformation_config = transformation_config
        self.camera_params = (
            transformation_config.undistort.camera_matrix[0][0],
            transformation_config.undistort.camera_matrix[1][1],
            transformation_config.undistort.camera_matrix[0][2],
            transformation_config.undistort.camera_matrix[1][2],
        )
        self.detector = detector

    async def handle_client(self, websocket):
        self.active_connections.add(websocket)
        print(f"Client connected. Active connections: {len(self.active_connections)}")

        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)

            if message == "request_frame":
                while True:
                    try:
                        success, frame = self.camera.read_local()

                        if not success or frame is None:
                            continue

                        frame = apply_all_transformations(
                            frame,
                            self.transformation_config,
                            self.camera_params,
                            self.detector,
                        )

                        _, buffer = cv2.imencode(".jpg", frame)
                        await asyncio.wait_for(
                            websocket.send(buffer.tobytes()), timeout=1.0
                        )
                    except (
                        asyncio.TimeoutError,
                        websockets.exceptions.ConnectionClosed,
                    ):
                        print("Send timeout or connection closed")
                        break

        except asyncio.TimeoutError:
            print("Initial message timeout")
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed during communication")

    async def start(self):
        self.ws_server = await websockets.serve(
            self.handle_client,
            "0.0.0.0",
            self.ws_listen_port,
            ping_interval=None,  # Disable automatic ping
            ping_timeout=None,  # Disable ping timeout
            close_timeout=1,  # Reduce close timeout
        )

        await self.ws_server.wait_closed()

    def set_no_read_mode(self, state: bool):
        self.no_read_mode = state
