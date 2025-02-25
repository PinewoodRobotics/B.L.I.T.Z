import cv2
import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
import os
import time
from project.common.camera.transform import unfisheye_image
from util import get_detector


def load_config(config_path="camera_config.json"):
    with open(config_path, "r") as f:
        return json.load(f)


def plot_top_down_view(tags, camera_matrix, dist_coeffs, tag_size):
    plt.clf()
    plt.xlim(-10, 10)
    plt.ylim(-10, 10)
    plt.xlabel("X Position (m)")
    plt.ylabel("Z Position (m)")
    plt.title("Top-Down View of Detected Tags")
    plt.grid(True)

    for tag in tags:
        if tag.pose_t is not None:
            x, y, z = tag.pose_t.flatten()  # Extract position
            plt.scatter(x, z, color="blue", s=100, label=f"Tag {tag.tag_id}")

            # Add tag ID and position text
            plt.text(
                x,
                z - 0.3,
                f"ID: {tag.tag_id}\n(x={x:.2f}, z={z:.2f})",
                ha="center",
                va="top",
                bbox=dict(facecolor="white", alpha=0.7),
            )

            # Draw orientation arrows with different colors and labels
            # Forward direction (Z-axis) - Red arrow
            plt.arrow(
                x,
                z,
                -tag.pose_R[2][0],
                tag.pose_R[2][2],
                head_width=0.1,
                head_length=0.1,
                fc="red",
                ec="red",
                label="Forward" if tag.tag_id == tags[0].tag_id else "",
            )

            # Right direction (X-axis) - Blue arrow
            plt.arrow(
                x,
                z,
                tag.pose_R[0][0],
                tag.pose_R[0][2],
                head_width=0.1,
                head_length=0.1,
                fc="blue",
                ec="blue",
                label="Right" if tag.tag_id == tags[0].tag_id else "",
            )

    plt.legend()
    plt.tight_layout()
    plt.pause(0.01)


def save_image(image):
    """Saves the image with a timestamped filename."""
    try:
        # Create absolute path for captures directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        save_dir = os.path.join(script_dir, "captures")

        # Ensure directory exists
        os.makedirs(save_dir, exist_ok=True)

        # Create filename with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(save_dir, f"capture_{timestamp}.png")

        # Force save without any dialog
        success = cv2.imwrite(filename, image)
        if success:
            print(f"Image saved: {filename}")
        else:
            print("Error: Failed to save image")
    except Exception as e:
        print(f"Error saving image: {e}")


def capture_and_detect():
    parser = argparse.ArgumentParser(
        description="Capture and detect AprilTags from camera"
    )
    parser.add_argument(
        "--camera", type=int, default=0, help="Camera device index (default: 0)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="camera_config.json",
        help="Path to config JSON file",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    camera_matrix = np.array(config["camera_params"]["camera_matrix"], dtype=np.float32)
    dist_coeffs = np.array(config["camera_params"]["dist_coeff"], dtype=np.float32)
    tag_size = config["tag_size_m"]

    # Initialize camera with retries
    max_retries = 5
    for attempt in range(max_retries):
        cap = cv2.VideoCapture(args.camera)
        if cap.isOpened():
            break
        print(f"Attempt {attempt + 1}/{max_retries} to open camera failed. Retrying...")
        time.sleep(1)

    if not cap.isOpened():
        print("Error: Could not open camera after multiple attempts")
        return

    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)  # Reduced from 100 to more stable 30 FPS
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize frame buffer

    detector = get_detector()

    # Create windows with specific flags for better stability
    cv2.namedWindow("Controls", cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_EXPANDED)
    cv2.namedWindow(
        "AprilTag Capture (Undistorted)", cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_EXPANDED
    )

    plt.ion()
    plt.figure("Top-Down View")  # Name the figure for better window management

    def update_control_panel(continuous_mode):
        control_panel = np.ones((180, 400, 3), dtype=np.uint8) * 255
        texts = [
            ("SPACE: Toggle detection mode", 30),
            (f"Current: {'Continuous' if continuous_mode else 'Manual'} Mode", 60),
            ("Press 's' to save undistorted frame", 90),
            ("Press 'q' to quit", 120),
        ]
        for text, y_pos in texts:
            cv2.putText(
                control_panel,
                text,
                (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 0),
                2,
            )
        return control_panel

    continuous_mode = True
    detected_tags = []
    last_frame_time = time.time()
    min_frame_time = 1.0 / 30.0  # Limit to 30 FPS for stability

    try:
        control_panel = update_control_panel(continuous_mode)
        cv2.imshow("Controls", control_panel)

        while True:
            # Maintain stable frame rate
            current_time = time.time()
            elapsed = current_time - last_frame_time
            if elapsed < min_frame_time:
                time.sleep(min_frame_time - elapsed)

            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame, retrying...")
                time.sleep(0.1)
                continue

            last_frame_time = time.time()

            # Process frame
            try:
                undistorted_frame, new_camera_matrix = unfisheye_image(
                    frame, camera_matrix, dist_coeffs
                )
                gray = cv2.cvtColor(undistorted_frame, cv2.COLOR_BGR2GRAY)

                # Extract updated camera parameters
                fx = new_camera_matrix[0, 0]
                fy = new_camera_matrix[1, 1]
                cx = new_camera_matrix[0, 2]
                cy = new_camera_matrix[1, 2]

                # Handle keyboard input - use waitKey with a timeout
                key = cv2.waitKey(1) & 0xFF

                # Save undistorted frame if 's' is pressed
                if key == ord("s"):
                    save_image(frame)

                # Toggle mode if space is pressed
                if key == ord(" "):
                    continuous_mode = not continuous_mode
                    control_panel = update_control_panel(continuous_mode)
                    cv2.imshow("Controls", control_panel)

                # Detect tags based on mode
                if continuous_mode or key == ord(" "):
                    detected_tags = detector.detect(
                        gray,
                        estimate_tag_pose=True,
                        camera_params=(fx, fy, cx, cy),
                        tag_size=tag_size,
                    )

                # Create display frame
                display_frame = undistorted_frame.copy()

                # Draw detections
                for tag in detected_tags:
                    # Draw tag outline
                    for i in range(4):
                        start = tuple(map(int, tag.corners[i]))
                        end = tuple(map(int, tag.corners[(i + 1) % 4]))
                        cv2.line(display_frame, start, end, (0, 255, 0), 2)

                    # Draw tag ID
                    center = tuple(map(int, tag.center))
                    cv2.putText(
                        display_frame,
                        f"ID: {tag.tag_id}",
                        (center[0] - 10, center[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 255),
                        2,
                    )

                    if tag.pose_t is not None and tag.pose_R is not None:
                        # Project 3D axes onto image
                        axes_length = 0.5
                        axes_points = np.array(
                            [
                                [0, 0, 0],
                                [axes_length, 0, 0],
                                [0, axes_length, 0],
                                [0, 0, axes_length],
                            ],
                            dtype=np.float32,
                        )

                        rotation_matrix = np.array(tag.pose_R, dtype=np.float32)
                        rvec = np.zeros((3, 1), dtype=np.float32)
                        cv2.Rodrigues(rotation_matrix, rvec)
                        tvec = np.array(tag.pose_t, dtype=np.float32).reshape(3, 1)

                        axes_points_2d, _ = cv2.projectPoints(
                            axes_points, rvec, tvec, new_camera_matrix, dist_coeffs
                        )
                        axes_points_2d = axes_points_2d.reshape(-1, 2)

                        # Draw axes
                        origin = tuple(map(int, axes_points_2d[0]))
                        x_point = tuple(map(int, axes_points_2d[1]))
                        y_point = tuple(map(int, axes_points_2d[2]))
                        z_point = tuple(map(int, axes_points_2d[3]))

                        cv2.line(display_frame, origin, x_point, (0, 0, 255), 2)
                        cv2.line(display_frame, origin, y_point, (0, 255, 0), 2)
                        cv2.line(display_frame, origin, z_point, (255, 0, 0), 2)

                # Draw detection count
                cv2.putText(
                    display_frame,
                    f"Detected Tags: {len(detected_tags)}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                )

                # Update displays
                if len(detected_tags) > 0:
                    try:
                        plot_top_down_view(
                            detected_tags, new_camera_matrix, dist_coeffs, tag_size
                        )
                    except Exception as e:
                        print(f"Error in plotting top-down view: {e}")

                cv2.imshow("AprilTag Capture (Undistorted)", display_frame)

                if key == ord("q"):
                    break

            except Exception as e:
                print(f"Error processing frame: {e}")
                continue

    except KeyboardInterrupt:
        print("\nGracefully shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        plt.ioff()
        plt.close("all")


if __name__ == "__main__":
    capture_and_detect()
