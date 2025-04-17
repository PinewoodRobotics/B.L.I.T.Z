from project.recognition.position.april.src.camera import CaptureDevice


def test_camera_open():
    camera = CaptureDevice(0, 640, 480, 30)
    assert camera.isOpened()
