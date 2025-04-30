import cv2
import os
from datetime import datetime


def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)

    photo_dir = "photos"
    if not os.path.exists(photo_dir):
        os.makedirs(photo_dir)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            continue

        copyframe = frame.copy()
        height, width = frame.shape[:2]
        center = (width // 2, height // 2)
        cv2.circle(frame, center, 5, (0, 0, 255), -1)

        cv2.imshow("Camera", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord(" "):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(photo_dir, f"photo_{timestamp}.png")
            cv2.imwrite(filename, copyframe)
            print(f"Photo saved as {filename}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
