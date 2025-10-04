import cv2
import os
import argparse
import numpy as np
import time


class DualVideoPlayer:
    """Dual video player implementation using only OpenCV"""

    def __init__(self, left_video_path=None, right_video_path=None):
        """Initialize the dual video player"""
        self.left_video_path = left_video_path
        self.right_video_path = right_video_path
        self.left_cap = None
        self.right_cap = None

        # Video state
        self.is_playing = True
        self.current_frame = 0
        self.total_frames = 0
        self.frame_delay = 30  # milliseconds between frames
        self.playback_speed = 1.0

        # Display parameters
        self.display_width = 1280  # total display width
        self.display_height = 480
        self.window_name = "Dual Camera Video Player"

        # Initialize videos if paths provided
        if left_video_path and right_video_path:
            self.load_videos(left_video_path, right_video_path)

    def load_videos(self, left_path, right_path):
        """Load video files"""
        # Open video captures
        if self.left_cap is not None:
            self.left_cap.release()
        if self.right_cap is not None:
            self.right_cap.release()

        self.left_cap = cv2.VideoCapture(left_path)
        self.right_cap = cv2.VideoCapture(right_path)

        # Check if videos opened successfully
        if not self.left_cap.isOpened() or not self.right_cap.isOpened():
            print(f"Error: Could not open one or both video files.")
            if not self.left_cap.isOpened():
                print(f"Left video '{left_path}' could not be opened.")
            if not self.right_cap.isOpened():
                print(f"Right video '{right_path}' could not be opened.")
            return False

        # Get video properties
        left_frames = int(self.left_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        right_frames = int(self.right_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.total_frames = min(left_frames, right_frames)

        # Reset to beginning
        self.current_frame = 0
        self.left_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.right_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        return True

    def seek(self, frame_number):
        """Seek to a specific frame number"""
        if self.left_cap is None or self.right_cap is None:
            return

        # Ensure frame number is within valid range
        frame_number = max(0, min(frame_number, self.total_frames - 1))

        # Set position in videos
        self.left_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.right_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

        # Update current frame
        self.current_frame = frame_number

    def get_frame_time(self, frame_number, fps):
        """Convert frame number to time string"""
        if fps <= 0:
            fps = 30  # Default if fps is invalid

        seconds = frame_number / fps
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def display_frame(self, left_frame, right_frame, fps):
        """Resize and display frames side by side with overlay information"""
        # Calculate individual frame width
        frame_width = self.display_width // 2

        # Resize frames to fit display
        if left_frame is not None:
            left_frame = cv2.resize(left_frame, (frame_width, self.display_height))
        else:
            left_frame = np.zeros((self.display_height, frame_width, 3), dtype=np.uint8)

        if right_frame is not None:
            right_frame = cv2.resize(right_frame, (frame_width, self.display_height))
        else:
            right_frame = np.zeros(
                (self.display_height, frame_width, 3), dtype=np.uint8
            )

        # Combine frames horizontally
        combined_frame = np.hstack((left_frame, right_frame))

        # Add overlay information
        if self.total_frames > 0:
            # Time information
            current_time = self.get_frame_time(self.current_frame, fps)
            total_time = self.get_frame_time(self.total_frames, fps)
            progress = int((self.current_frame / self.total_frames) * 100)
            time_text = f"{current_time} / {total_time} ({progress}%)"

            # Add progress bar
            bar_width = int(
                (self.current_frame / self.total_frames) * self.display_width
            )
            cv2.rectangle(
                combined_frame,
                (0, self.display_height - 20),
                (bar_width, self.display_height - 10),
                (0, 255, 0),
                -1,
            )
            cv2.rectangle(
                combined_frame,
                (0, self.display_height - 20),
                (self.display_width, self.display_height - 10),
                (255, 255, 255),
                1,
            )

            # Display time and frame info
            cv2.putText(
                combined_frame,
                time_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            # Display playback info
            status = "Playing" if self.is_playing else "Paused"
            speed_text = f"Speed: {self.playback_speed:.2f}x"
            cv2.putText(
                combined_frame,
                f"{status} | {speed_text}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

        # Display help text
        help_text = (
            "Space: Play/Pause | Left/Right: -/+ 10 frames | Up/Down: Speed | Q: Quit"
        )
        cv2.putText(
            combined_frame,
            help_text,
            (10, self.display_height - 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

        # Left/Right labels
        cv2.putText(
            combined_frame,
            "LEFT",
            (10, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            combined_frame,
            "RIGHT",
            (frame_width + 10, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        # Show the combined frame
        cv2.imshow(self.window_name, combined_frame)

    def run(self):
        """Main playback loop"""
        if self.left_cap is None or self.right_cap is None:
            print("No videos loaded. Please load videos first.")
            return

        # Create window
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.display_width, self.display_height)

        # Get FPS from left video
        fps = self.left_cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30  # Default if fps is invalid

        last_frame_time = time.time()

        while True:
            # Handle frame timing for playback speed
            current_time = time.time()
            time_diff = (current_time - last_frame_time) * 1000  # ms

            # Read frames if playing and enough time has passed
            if self.is_playing and time_diff >= (
                self.frame_delay / self.playback_speed
            ):
                # Read frames
                left_ret, left_frame = self.left_cap.read()
                right_ret, right_frame = self.right_cap.read()

                # Check if we reached the end
                if not left_ret or not right_ret:
                    # Loop back to beginning
                    self.seek(0)
                    left_ret, left_frame = self.left_cap.read()
                    right_ret, right_frame = self.right_cap.read()

                # Update frame counter
                self.current_frame += 1

                # Update last frame time
                last_frame_time = current_time
            else:
                # If paused, just use current frames
                self.left_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                self.right_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                left_ret, left_frame = self.left_cap.read()
                right_ret, right_frame = self.right_cap.read()

            # Display the frames
            self.display_frame(
                left_frame if left_ret else None,
                right_frame if right_ret else None,
                fps,
            )

            # Handle keyboard input with short delay
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:  # q or ESC to quit
                break
            elif key == ord(" "):  # Space to play/pause
                self.is_playing = not self.is_playing
            elif key == ord(",") or key == 81:  # Left arrow or comma: back 10 frames
                self.seek(self.current_frame - 10)
            elif (
                key == ord(".") or key == 83
            ):  # Right arrow or period: forward 10 frames
                self.seek(self.current_frame + 10)
            elif key == 82:  # Up arrow: increase speed
                self.playback_speed = min(4.0, self.playback_speed + 0.25)
            elif key == 84:  # Down arrow: decrease speed
                self.playback_speed = max(0.25, self.playback_speed - 0.25)
            elif key == ord("r"):  # r: reset to beginning
                self.seek(0)

        # Clean up
        self.left_cap.release()
        self.right_cap.release()
        cv2.destroyAllWindows()


def file_selector():
    """Simple command-line file selection"""
    print("Select left video file:")
    left_path = input("Enter full path: ").strip()

    print("Select right video file:")
    right_path = input("Enter full path: ").strip()

    if not os.path.exists(left_path):
        print(f"Error: Left video file not found: {left_path}")
        return None, None

    if not os.path.exists(right_path):
        print(f"Error: Right video file not found: {right_path}")
        return None, None

    return left_path, right_path


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Dual Camera Video Player")
    parser.add_argument("--left", help="Path to left camera video")
    parser.add_argument("--right", help="Path to right camera video")
    args = parser.parse_args()

    # Get video paths
    left_path = args.left
    right_path = args.right

    # If no paths provided, use interactive selection
    if not left_path or not right_path:
        left_path, right_path = file_selector()

    # Create player
    if left_path and right_path:
        player = DualVideoPlayer(left_path, right_path)
        player.run()
    else:
        print("No video files specified. Exiting.")


if __name__ == "__main__":
    main()
