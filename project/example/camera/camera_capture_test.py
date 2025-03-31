import cv2
import numpy as np

# Define camera intrinsic parameters
camera_matrix = np.array(
    [[512.71702172, 0, 410.11248372], [0, 515.49273551, 322.10292672], [0, 0, 1]]
)

dist_coeff = np.array([0.05091232, -0.11548729, 0.00114166, -0.00130648, 0.03452092])

# Open camera
camera = cv2.VideoCapture(0)  # Use correct index or device path

# Set specific resolution (640x480)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not camera.isOpened():
    print("Error: Cannot open camera")
    exit()

# Print actual resolution (might be different from requested)
actual_width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
actual_height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
print(f"Camera resolution: {actual_width}x{actual_height}")

while True:
    ret, frame = camera.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Undistort frame using the camera parameters
    h, w = frame.shape[:2]
    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
        camera_matrix, dist_coeff, (w, h), 1, (w, h)
    )
    undistorted_frame = cv2.undistort(
        frame, camera_matrix, dist_coeff, None, new_camera_matrix
    )

    # Display both original and undistorted frames
    cv2.imshow("Original", frame)
    cv2.imshow("Undistorted", undistorted_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):  # Press 'q' to quit
        break

camera.release()
cv2.destroyAllWindows()
