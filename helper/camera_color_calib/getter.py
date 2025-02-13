import cv2
import os
from typing import Optional, Tuple


def init_camera(camera_id: int = 0) -> Tuple[cv2.VideoCapture, Tuple[int, int]]:
    """
    Initialize the camera and get its properties.

    Args:
        camera_id (int): Camera device ID (usually 0 for built-in webcam)

    Returns:
        Tuple[cv2.VideoCapture, Tuple[int, int]]: Camera object and frame dimensions
    """
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open camera {camera_id}")

    # Get frame dimensions
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    return cap, (width, height)


def capture_images(save_dir: Optional[str] = None, camera_id: int = 0) -> str:
    """
    Capture images from camera and save them to directory.

    Args:
        save_dir (str, optional): Directory to save images. Creates 'captured_images' if None
        camera_id (int): Camera device ID

    Returns:
        str: Path to the directory containing captured images

    Controls:
        - SPACE: Capture image
        - ESC: Exit capture mode
    """
    # Setup save directory
    if save_dir is None:
        save_dir = "captured_images"
    os.makedirs(save_dir, exist_ok=True)

    # Initialize camera
    cap, (width, height) = init_camera(camera_id)

    image_count = 0
    print("Press SPACE to capture an image, ESC to finish")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            # Show live feed
            cv2.imshow("Camera Feed", frame)

            # Handle key presses
            key = cv2.waitKey(1) & 0xFF

            if key == ord(" "):  # SPACE to capture
                image_path = os.path.join(save_dir, f"image_{image_count:03d}.jpg")
                cv2.imwrite(image_path, frame)
                print(f"Captured image saved to: {image_path}")
                image_count += 1

            elif key == 27:  # ESC to exit
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

    if image_count == 0:
        raise RuntimeError("No images were captured!")

    print(f"Captured {image_count} images in {save_dir}")
    return save_dir


if __name__ == "__main__":
    # Test the camera capture
    try:
        save_dir = capture_images()
        print(f"Images saved to: {save_dir}")
    except Exception as e:
        print(f"Error: {e}")
