from typing import override
from cscore import UsbCamera, CvSink, VideoCamera, VideoMode, VideoSource

from blitz.recognition.position.april.src.camera.abstract_camera import (
    AbstractCaptureDevice,
    CameraType,
)


class OV2311Camera(AbstractCaptureDevice, type=CameraType.OV2311):
    @override
    def _configure_camera(self):
        self.camera: VideoSource | None = UsbCamera("CAMERA", self.port)
        _ = self.camera.setResolution(self.width, self.height)
        _ = self.camera.setFPS(self.max_fps)
        _ = self.camera.setPixelFormat(VideoMode.PixelFormat.kMJPEG)
        self.sink: CvSink | None = CvSink(self.camera.getName())
        self.sink.setSource(self.camera)
        if self.exposure_time is not None:
            self.camera.setExposureManual(self.exposure_time)
