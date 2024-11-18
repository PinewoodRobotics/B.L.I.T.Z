import asyncio
import time
from typing import Optional
import cv2
import nats
import numpy as np
import pyapriltags
from pyinstrument import Profiler
from nats.aio.msg import Msg


async def main():
    profiler = Profiler()
    profiler.start()

    cap = cv2.VideoCapture(0)
    detector = pyapriltags.Detector()

    while True:
        _, frame = cap.read()

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        detections = detector.detect(
            frame_gray,
        )

        print(detections)

        for detection in detections:
            corners = [tuple(map(int, corner)) for corner in detection.corners]

            cv2.polylines(
                frame,
                [np.array(corners, dtype=np.int32)],
                isClosed=True,
                color=(0, 255, 0),
                thickness=4,
            )

            tag_id = detection.tag_id
            cv2.putText(
                frame,
                f"ID: {tag_id}",
                (corners[0][0], corners[0][1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                3,
            )

        cv2.imshow("frame", frame)
        cv2.waitKey(1)


if __name__ == "__main__":
    asyncio.run(main())
