import cv2
import numpy as np

# Define checkerboard size (use a standard pattern, e.g., 9x6)
CHECKERBOARD = (18, 11)
square_size = 1.0  # Set based on the actual size of the checkerboard squares

# Prepare object points based on the checkerboard pattern
objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0 : CHECKERBOARD[0], 0 : CHECKERBOARD[1]].T.reshape(-1, 2)
objp *= square_size

# Arrays to store object points and image points
objpoints = []  # 3D points in real-world space
imgpoints = []  # 2D points in image plane

# Start capturing from the webcam
cap = cv2.VideoCapture(0)
print("Press 'c' to capture a chessboard frame for calibration, or 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture image.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Find the chessboard corners
    ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)

    # If found, display the corners
    if ret:
        cv2.drawChessboardCorners(frame, CHECKERBOARD, corners, ret)
        print("Chessboard detected. Ready to capture.")
    else:
        print("Chessboard not found. Adjust the pattern or position.")

    # Show the live video feed with drawn corners if detected
    cv2.imshow("Calibration Frame", frame)

    # Press 'c' to capture the frame for calibration, or 'q' to quit
    key = cv2.waitKey(10) & 0xFF  # Wait for key press and mask the value
    if key == ord("c") and ret:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(
            gray,
            corners,
            (11, 11),
            (-1, -1),
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001),
        )
        imgpoints.append(corners2)
        print("Captured frame for calibration.")
    elif key == ord("q"):
        print("Exiting capture loop.")
        break

# Release the capture and close windows
cap.release()
cv2.destroyAllWindows()

# Check if enough frames were captured for calibration
if len(objpoints) < 10:
    print(
        "Not enough frames captured for calibration. At least 10 images are recommended."
    )
else:
    # Calibrate the fisheye camera
    K = np.zeros((3, 3))
    D = np.zeros((4, 1))
    ret, K, D, rvecs, tvecs = cv2.fisheye.calibrate(
        objpoints,
        imgpoints,
        gray.shape[::-1],
        K,
        D,
        None,
        None,
        cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC,
        criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-6),
    )

    # Save the calibration data
    np.savez("fisheye_calibration_data.npz", K=K, D=D)
    print("Fisheye calibration data saved.")
