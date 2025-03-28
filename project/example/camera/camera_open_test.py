import cv2


port = "/dev/video-rear-right"
video_capture = cv2.VideoCapture(port)
print(f"Opening camera on port {port}: {video_capture.isOpened()}")
