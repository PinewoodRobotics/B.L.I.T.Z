import cv2
import os
from datetime import datetime


def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    video_dir = "videos"
    if not os.path.exists(video_dir):
        os.makedirs(video_dir)

    is_recording = False
    out = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if is_recording:
            out.write(frame)
            cv2.putText(
                frame,
                "RECORDING",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )

        cv2.putText(
            frame,
            "Press 'r' to start/stop recording",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            frame,
            "Press 'q' to quit",
            (10, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        cv2.imshow("Camera", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            if not is_recording:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(video_dir, f"video_{timestamp}.mp4")
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
                is_recording = True
                print(f"Started recording: {filename}")
            else:
                is_recording = False
                if out is not None:
                    out.release()
                print("Stopped recording")

    if is_recording and out is not None:
        out.release()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
