import asyncio
import cv2
import nats
from project.common.image.query_helper.april_query_helper import AprilQueryHelper
from nats.aio.client import Client

from project.example.util.render.april_tag import render_april_tag


async def main():
    april_tag_detection_helper = AprilQueryHelper(
        nats_client=await nats.connect("nats://localhost:4222"),
        input_topic="apriltag/tag",
        output_topic="apriltag/camera",
    )
    await april_tag_detection_helper.begin_subscribe()
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        print("!!!")
        res = await april_tag_detection_helper.send_and_wait_for_response(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), "left"
        )
        frame = render_april_tag(frame, res)

        cv2.imshow("frame", frame)
        cv2.waitKey(1)


if __name__ == "__main__":
    asyncio.run(main())
