from cscore import UsbCamera, CvSink, VideoMode

from blitz.recognition.position.april.src.camera.abstract_camera import (
    AbstractCaptureDevice,
    CameraType,
)


class OV2311Camera(AbstractCaptureDevice, type=CameraType.OV2311):
    def _configure_camera(self):
        self.camera = UsbCamera("CAMERA", self.port)
        self.camera.setResolution(self.width, self.height)
        self.camera.setFPS(self.max_fps)
        self.sink = CvSink(self.camera.getName())
        self.sink.setSource(self.camera)
        if self.exposure_time is not None:
            self.camera.setExposureManual(self.exposure_time)
