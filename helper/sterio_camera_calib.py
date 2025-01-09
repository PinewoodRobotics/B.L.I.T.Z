import cv2
import numpy as np
import os
import json
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QCheckBox,
    QWidget,
    QMessageBox,
)


class StereoCalibrationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stereo Calibration App")
        self.setGeometry(100, 100, 800, 600)

        self.image_folder = "stereo_images"
        os.makedirs(self.image_folder, exist_ok=True)
        self.calibration_file = "calibration_data.json"
        self.chessboard_size = (8, 6)  # Adjust this to match your chessboard corners
        self.square_size = 0.025  # in meters

        # Flag to determine if user confirmation is required
        self.auto_save = False

        # Layout and widgets
        self.layout = QVBoxLayout()
        self.capture_button = QPushButton("Capture Stereo Images")
        self.calibrate_button = QPushButton("Calibrate Cameras")
        self.rectify_button = QPushButton("Rectify Images")
        self.triangulate_button = QPushButton("Triangulate Points")
        self.image_label = QLabel("Stereo Calibration App")
        self.auto_save_checkbox = QCheckBox("Enable Auto Save (No Confirmation)")

        self.layout.addWidget(self.capture_button)
        self.layout.addWidget(self.calibrate_button)
        self.layout.addWidget(self.rectify_button)
        self.layout.addWidget(self.triangulate_button)
        self.layout.addWidget(self.auto_save_checkbox)
        self.layout.addWidget(self.image_label)

        # Set up QWidget
        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        # Bind buttons
        self.capture_button.clicked.connect(self.capture_images)
        self.calibrate_button.clicked.connect(self.calibrate_cameras)
        self.rectify_button.clicked.connect(self.rectify_images)
        self.triangulate_button.clicked.connect(self.triangulate_points)

        # Bind checkbox
        self.auto_save_checkbox.stateChanged.connect(self.toggle_auto_save)

        # Variables for calibration
        self.object_points = []
        self.image_points_left = []
        self.image_points_right = []
        self.K_left, self.D_left = None, None
        self.K_right, self.D_right = None, None
        self.R, self.T = None, None

        # Load calibration data if available
        self.load_calibration_data()

    def toggle_auto_save(self, state):
        self.auto_save = state == 2  # 2 means the checkbox is checked

    def load_calibration_data(self):
        if os.path.exists(self.calibration_file):
            with open(self.calibration_file, "r") as f:
                data = json.load(f)
                self.K_left = np.array(data["K_left"])
                self.D_left = np.array(data["D_left"])
                self.K_right = np.array(data["K_right"])
                self.D_right = np.array(data["D_right"])
                self.R = np.array(data["R"])
                self.T = np.array(data["T"])
                self.image_label.setText("Calibration data loaded successfully")
        else:
            self.image_label.setText("No calibration data found")

    def capture_images(self):
        cap_left = cv2.VideoCapture(0)  # Left camera
        cap_right = cv2.VideoCapture(1)  # Right camera

        if not cap_left.isOpened() or not cap_right.isOpened():
            self.image_label.setText("Error: Cameras not detected")
            return

        count = 0
        while count < 10:  # Capture 10 stereo image pairs
            ret_left, frame_left = cap_left.read()
            ret_right, frame_right = cap_right.read()

            if not ret_left or not ret_right:
                continue

            # Make copies of the frames for displaying overlays
            display_frame_left = frame_left.copy()
            display_frame_right = frame_right.copy()

            # Detect chessboard in both images
            gray_left = cv2.cvtColor(frame_left, cv2.COLOR_BGR2GRAY)
            gray_right = cv2.cvtColor(frame_right, cv2.COLOR_BGR2GRAY)
            ret_left, corners_left = cv2.findChessboardCorners(
                gray_left, self.chessboard_size
            )
            ret_right, corners_right = cv2.findChessboardCorners(
                gray_right, self.chessboard_size
            )

            # Draw detected corners on the display frames
            if ret_left:
                cv2.drawChessboardCorners(
                    display_frame_left, self.chessboard_size, corners_left, ret_left
                )
            if ret_right:
                cv2.drawChessboardCorners(
                    display_frame_right, self.chessboard_size, corners_right, ret_right
                )

            # Show live feed from both cameras with overlays
            combined_frame = np.hstack((display_frame_left, display_frame_right))
            cv2.imshow("Stereo Camera Feed", combined_frame)

            # If chessboards are detected in both cameras
            if ret_left and ret_right:
                if self.auto_save:
                    # Auto-save mode
                    cv2.imwrite(
                        os.path.join(self.image_folder, f"left_{count}.jpg"), frame_left
                    )
                    cv2.imwrite(
                        os.path.join(self.image_folder, f"right_{count}.jpg"),
                        frame_right,
                    )
                    count += 1
                    self.image_label.setText(f"Saved pair {count}")
                else:
                    # User confirmation mode
                    user_input = QMessageBox.question(
                        self,
                        "Save Frame?",
                        "Chessboard detected in both cameras. Do you want to save this frame?",
                        QMessageBox.Yes | QMessageBox.No,
                    )

                    if user_input == QMessageBox.Yes:
                        # Save the original frames, not the ones with overlays
                        cv2.imwrite(
                            os.path.join(self.image_folder, f"left_{count}.jpg"),
                            frame_left,
                        )
                        cv2.imwrite(
                            os.path.join(self.image_folder, f"right_{count}.jpg"),
                            frame_right,
                        )
                        count += 1
                        self.image_label.setText(f"Saved pair {count}")
                    else:
                        self.image_label.setText("Frame discarded")

            # Exit the loop if 'q' is pressed
            key = cv2.waitKey(1)
            if key == ord("q"):
                break

        cap_left.release()
        cap_right.release()
        cv2.destroyAllWindows()
        self.image_label.setText("Image capture completed")

    def calibrate_cameras(self):
        object_point = np.zeros(
            (self.chessboard_size[0] * self.chessboard_size[1], 3), np.float32
        )
        object_point[:, :2] = np.mgrid[
            0 : self.chessboard_size[0], 0 : self.chessboard_size[1]
        ].T.reshape(-1, 2)
        object_point *= self.square_size

        self.object_points = []  # Reset for new calibration
        self.image_points_left = []
        self.image_points_right = []

        image_files = sorted(
            [
                f
                for f in os.listdir(self.image_folder)
                if f.startswith("left_") or f.startswith("right_")
            ]
        )
        num_pairs = len(image_files) // 2  # Calculate number of pairs

        for i in range(num_pairs):  # Dynamically determine the number of image pairs
            left_image = cv2.imread(os.path.join(self.image_folder, f"left_{i}.jpg"))
            right_image = cv2.imread(os.path.join(self.image_folder, f"right_{i}.jpg"))

            if left_image is None or right_image is None:
                continue

            gray_left = cv2.cvtColor(left_image, cv2.COLOR_BGR2GRAY)
            gray_right = cv2.cvtColor(right_image, cv2.COLOR_BGR2GRAY)

            ret_left, corners_left = cv2.findChessboardCorners(
                gray_left, self.chessboard_size
            )
            ret_right, corners_right = cv2.findChessboardCorners(
                gray_right, self.chessboard_size
            )

            if ret_left and ret_right:
                self.object_points.append(object_point)
                self.image_points_left.append(corners_left)
                self.image_points_right.append(corners_right)

        if len(self.object_points) == 0:
            self.image_label.setText("Calibration failed: No chessboards detected")
            return

        # Calibrate left and right cameras individually
        ret_left, self.K_left, self.D_left, rvecs_left, tvecs_left = (
            cv2.calibrateCamera(
                self.object_points,
                self.image_points_left,
                gray_left.shape[::-1],
                None,
                None,
            )
        )
        ret_right, self.K_right, self.D_right, rvecs_right, tvecs_right = (
            cv2.calibrateCamera(
                self.object_points,
                self.image_points_right,
                gray_right.shape[::-1],
                None,
                None,
            )
        )

        # Stereo calibration
        (
            ret_stereo,
            self.K_left,
            self.D_left,
            self.K_right,
            self.D_right,
            self.R,
            self.T,
            E,
            F,
        ) = cv2.stereoCalibrate(
            self.object_points,
            self.image_points_left,
            self.image_points_right,
            self.K_left,
            self.D_left,
            self.K_right,
            self.D_right,
            gray_left.shape[::-1],
            flags=cv2.CALIB_FIX_INTRINSIC,
        )

        # Calculate reprojection error
        total_error = 0
        total_points = 0

        for i in range(len(self.object_points)):
            # Reproject points for left and right cameras
            img_points_left_reproj, _ = cv2.projectPoints(
                self.object_points[i],
                rvecs_left[i],
                tvecs_left[i],
                self.K_left,
                self.D_left,
            )
            img_points_right_reproj, _ = cv2.projectPoints(
                self.object_points[i],
                rvecs_right[i],
                tvecs_right[i],
                self.K_right,
                self.D_right,
            )

            # Compute the error for each point
            error_left = cv2.norm(
                self.image_points_left[i], img_points_left_reproj, cv2.NORM_L2
            )
            error_right = cv2.norm(
                self.image_points_right[i], img_points_right_reproj, cv2.NORM_L2
            )

            total_error += error_left**2 + error_right**2
            total_points += len(self.object_points[i])

        # Compute the mean error
        reprojection_error = np.sqrt(total_error / total_points)

        # Save the calibration data for both cameras
        calibration_data = {
            "K_left": self.K_left.tolist(),
            "D_left": self.D_left.tolist(),
            "K_right": self.K_right.tolist(),
            "D_right": self.D_right.tolist(),
            "R": self.R.tolist(),
            "T": self.T.tolist(),
            "reprojection_error": reprojection_error,
        }
        with open(self.calibration_file, "w") as f:
            json.dump(calibration_data, f, indent=4)

        # Save individual configurations
        left_config = {
            "camera_matrix": self.K_left.tolist(),
            "dist_coeffs": self.D_left.tolist(),
        }
        right_config = {
            "camera_matrix": self.K_right.tolist(),
            "dist_coeffs": self.D_right.tolist(),
        }

        with open("left_camera_config.json", "w") as f_left:
            json.dump(left_config, f_left, indent=4)

        with open("right_camera_config.json", "w") as f_right:
            json.dump(right_config, f_right, indent=4)

        self.image_label.setText(
            f"Calibration Completed with reprojection error: {reprojection_error:.4f}"
        )

    def rectify_images(self):
        if self.K_left is None or self.K_right is None:
            QMessageBox.warning(self, "Error", "Please calibrate the cameras first!")
            return

        left_image = cv2.imread(os.path.join(self.image_folder, "left_0.jpg"))
        right_image = cv2.imread(os.path.join(self.image_folder, "right_0.jpg"))

        if left_image is None or right_image is None:
            QMessageBox.warning(self, "Error", "Calibration images not found!")
            return

        h, w = left_image.shape[:2]
        R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(
            self.K_left, self.D_left, self.K_right, self.D_right, (w, h), self.R, self.T
        )

        map_left_x, map_left_y = cv2.initUndistortRectifyMap(
            self.K_left, self.D_left, R1, P1, (w, h), cv2.CV_32FC1
        )
        map_right_x, map_right_y = cv2.initUndistortRectifyMap(
            self.K_right, self.D_right, R2, P2, (w, h), cv2.CV_32FC1
        )

        rectified_left = cv2.remap(left_image, map_left_x, map_left_y, cv2.INTER_LINEAR)
        rectified_right = cv2.remap(
            right_image, map_right_x, map_right_y, cv2.INTER_LINEAR
        )

        cv2.imshow("Rectified Left", rectified_left)
        cv2.imshow("Rectified Right", rectified_right)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def triangulate_points(self):
        if self.K_left is None or self.K_right is None:
            QMessageBox.warning(self, "Error", "Please calibrate the cameras first!")
            return

        left_image_path = os.path.join(self.image_folder, "left_0.jpg")
        right_image_path = os.path.join(self.image_folder, "right_0.jpg")

        left_image = cv2.imread(left_image_path)
        right_image = cv2.imread(right_image_path)

        if left_image is None or right_image is None:
            QMessageBox.warning(self, "Error", "Rectified images not found!")
            return

        h, w = left_image.shape[:2]
        R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(
            self.K_left, self.D_left, self.K_right, self.D_right, (w, h), self.R, self.T
        )

        # Convert images to grayscale
        gray_left = cv2.cvtColor(left_image, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(right_image, cv2.COLOR_BGR2GRAY)

        # Find chessboard corners
        ret_left, corners_left = cv2.findChessboardCorners(
            gray_left, self.chessboard_size, None
        )
        ret_right, corners_right = cv2.findChessboardCorners(
            gray_right, self.chessboard_size, None
        )

        if not ret_left or not ret_right:
            QMessageBox.warning(
                self, "Error", "Chessboard corners not detected in one or both images!"
            )
            return

        # Refine corner positions for better accuracy
        corners_left = cv2.cornerSubPix(
            gray_left,
            corners_left,
            (11, 11),
            (-1, -1),
            criteria=cv2.TermCriteria(
                cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001
            ),
        )
        corners_right = cv2.cornerSubPix(
            gray_right,
            corners_right,
            (11, 11),
            (-1, -1),
            criteria=cv2.TermCriteria(
                cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001
            ),
        )

        # Triangulate points
        points_4d_homogeneous = cv2.triangulatePoints(
            P1, P2, corners_left, corners_right
        )

        # Convert homogeneous coordinates to 3D
        points_3d = cv2.convertPointsFromHomogeneous(points_4d_homogeneous.T)

        # Display the results
        print("Triangulated 3D Points:")
        for i, point in enumerate(points_3d):
            print(f"Point {i + 1}: {point.ravel()}")

        QMessageBox.information(self, "Info", "Triangulation completed!")


if __name__ == "__main__":
    app = QApplication([])
    window = StereoCalibrationApp()
    window.show()
    app.exec_()
