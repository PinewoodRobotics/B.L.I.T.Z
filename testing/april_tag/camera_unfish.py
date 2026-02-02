import time
import cv2
import numpy as np


CAMERA_MATRIX = np.array([
    [644.12542785, 0., 318.47939346],
    [0., 639.36517808, 218.74994066],
    [0., 0., 1.],
])
DIST_COEFF = np.array([-0.43899338, 0.33405716, 0.00489076, -0.00426836, -0.3116031])

def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    while True:
        _, frame = cap.read()
        current_time = time.time() * 1000
        _ = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        unfisheye_image = cv2.undistort(frame, CAMERA_MATRIX, DIST_COEFF)
        print(unfisheye_image.shape)
        print(f"time: {time.time() * 1000 - current_time}")
        cv2.imshow("frame", unfisheye_image)
        cv2.waitKey(1)

if __name__ == "__main__":
    main()