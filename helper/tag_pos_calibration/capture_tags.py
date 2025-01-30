import cv2
import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
import pyapriltags  # Import apriltag for the detector
import os
import time
from project.common.camera.transform import unfisheye_image
from util import get_detector


def load_config(config_path="camera_config.json"):
    with open(config_path, "r") as f:
        return json.load(f)


def plot_top_down_view(tags, camera_matrix, dist_coeffs, tag_size):
    plt.clf()
    plt.xlim(-5, 5)
    plt.ylim(-5, 5)
    plt.xlabel("X Position (m)")
    plt.ylabel("Z Position (m)")
    plt.title("Top-Down View of Detected Tags")

    for tag in tags:
        if tag.pose_t is not None:
            x, _, z = tag.pose_t.flatten()  # Extract X and Z position
            plt.scatter(x, z, color="blue", label=f"Tag {tag.tag_id}")
            plt.arrow(
                x,
                z,
                tag.pose_R[2][0],
                tag.pose_R[2][2],
                head_width=0.05,
                head_length=0.05,
                fc="red",
                ec="red",
            )

            plt.arrow(
                x,
                z,
                tag.pose_R[0][0],
                tag.pose_R[0][2],
                head_width=0.05,
                head_length=0.05,
                fc="blue",
                ec="blue",
            )

    plt.pause(0.01)


def save_image(image):
    """Saves the image with a timestamped filename."""
    save_dir = "captures"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(save_dir, f"capture_{timestamp}.png")
    cv2.imwrite(filename, image)
    print(f"Image saved: {filename}")


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

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 100)
    if not cap.isOpened():
        print("Error: Could not open camera")
        return

    detector = get_detector()
    plt.ion()

    print("Controls:")
    print("  - Press 's' to manually save the current frame")
    print("  - Press 'q' to quit")

    last_save_time = time.time()  # Track last auto-save

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame")
            break

        # Unfisheye the image first
        undistorted_frame, new_camera_matrix = unfisheye_image(
            frame, camera_matrix, dist_coeffs
        )

        # Convert to grayscale
        gray = cv2.cvtColor(undistorted_frame, cv2.COLOR_BGR2GRAY)

        # Extract updated focal length and optical center from the new camera matrix
        fx = new_camera_matrix[0, 0]  # Updated focal length in x
        fy = new_camera_matrix[1, 1]  # Updated focal length in y
        cx = new_camera_matrix[0, 2]  # Updated optical center x
        cy = new_camera_matrix[1, 2]  # Updated optical center y

        # Detect AprilTags
        tags = detector.detect(
            gray,
            estimate_tag_pose=True,
            camera_params=(fx, fy, cx, cy),
            tag_size=tag_size,
        )

        for tag in tags:
            for i in range(4):
                start = tuple(map(int, tag.corners[i]))
                end = tuple(map(int, tag.corners[(i + 1) % 4]))
                cv2.line(undistorted_frame, start, end, (0, 255, 0), 2)

            center = tuple(map(int, tag.center))
            cv2.putText(
                undistorted_frame,
                f"ID: {tag.tag_id}",
                (center[0] - 10, center[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                2,
            )

        cv2.putText(
            undistorted_frame,
            f"Detected Tags: {len(tags)}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

        if len(tags) > 0:
            plot_top_down_view(tags, new_camera_matrix, dist_coeffs, tag_size)

        cv2.imshow("AprilTag Capture (Undistorted)", undistorted_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

        # Save manually if 's' is pressed
        if key == ord("s"):
            save_image(frame)

        # Auto-save every 2 seconds
        if time.time() - last_save_time >= 2:
            save_image(frame)
            last_save_time = time.time()  # Update last save time

    cap.release()
    cv2.destroyAllWindows()
    plt.ioff()
    plt.show()


if __name__ == "__main__":
    capture_and_detect()
