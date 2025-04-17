import cv2
import os
from datetime import datetime


def main():
    cap = cv2.VideoCapture(0)
    photo_dir = "photos"
    if not os.path.exists(photo_dir):
        os.makedirs(photo_dir)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow("Camera", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord(" "):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(photo_dir, f"photo_{timestamp}.png")
            cv2.imwrite(filename, frame)
            print(f"Photo saved as {filename}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
