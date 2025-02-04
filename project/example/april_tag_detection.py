import asyncio
import cv2
from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.config_class.profiler import ProfilerConfig
from project.common.debug.profiler import init_profiler
from project.common.image.query_helper.april_query_helper import AprilQueryHelper

from project.example.util.render.april_tag import render_april_tag


init_profiler(
    ProfilerConfig(
        {
            "activated": True,
            "output-file": "profiler.html",
            "profile-function": True,
            "time-function": False,
        }
    )
)


async def main():
    autobahn_server = Autobahn("localhost", 8080)
    await autobahn_server.begin()
    april_tag_detection_helper = AprilQueryHelper(
        autobahn_server=autobahn_server,
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
