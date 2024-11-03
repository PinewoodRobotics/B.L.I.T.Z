import cv2
import numpy as np
import glob

# Termination criteria for corner subpixel accuracy
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# Chessboard dimensions (adjust to your actual chessboard pattern)
chessboard_size = (7, 6)
square_size = 1.0  # Change according to your chessboard square size in your preferred unit (e.g., 1 cm)

# Prepare object points based on the actual chessboard pattern
objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
objp[:, :2] = np.mgrid[0 : chessboard_size[0], 0 : chessboard_size[1]].T.reshape(-1, 2)
objp *= square_size

# Arrays to store object points and image points from all frames
objpoints = []  # 3D points in real-world space
imgpoints = []  # 2D points in image plane

# Start capturing images from the webcam
cap = cv2.VideoCapture(0)
print("Press 'c' to capture a chessboard frame, or 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture image.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Find the chessboard corners
    ret, corners = cv2.findChessboardCorners(gray, chessboard_size, None)

    # If found, add object points, image points (after refining them)
    if ret:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)

        # Draw and display the corners
        cv2.drawChessboardCorners(frame, chessboard_size, corners2, ret)
        print("Chessboard captured.")

    cv2.imshow("Calibration Frame", frame)

    # Press 'c' to capture and store the frame or 'q' to quit
    key = cv2.waitKey(1)
    if key == ord("c") and ret:
        print("Captured frame.")
    elif key == ord("q"):
        print("Quitting...")
        break

# Release the capture and close windows
cap.release()
cv2.destroyAllWindows()

# Perform calibration if we have enough captured images
if len(objpoints) > 10:  # At least 10 images are recommended
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, gray.shape[::-1], None, None
    )

    # Print and save calibration data
    print("Camera matrix:\n", mtx)
    print("Distortion coefficients:\n", dist)

    # Save the calibration results for future use
    np.savez("calibration_data.npz", mtx=mtx, dist=dist, rvecs=rvecs, tvecs=tvecs)
    print("Calibration data saved.")
else:
    print(
        "Not enough frames captured for calibration. Try capturing more chessboard images."
    )
