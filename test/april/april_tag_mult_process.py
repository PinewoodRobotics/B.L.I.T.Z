import asyncio
import time
from typing import Optional
import cv2
import nats
import numpy as np
import pyapriltags
from pyinstrument import Profiler
from nats.aio.msg import Msg
import msgpack
import msgpack_numpy as m

from common import profiler
from common.config_class.profiler import ProfilerConfig
from generated.common.proto.AprilTag_pb2 import AprilTags
from generated.common.proto.Image_pb2 import ImageMessage


async def main():
    profiler.init_profiler(
        ProfilerConfig(
            {
                "activated": True,
                "output-file": "profiler.html",
                "profile-function": True,
                "time-function": True,
            }
        )
    )

    april_tags: AprilTags | None = None

    cap = cv2.VideoCapture(0)
    nt = await nats.connect(f"nats://localhost:4222")

    async def on_message(msg: Msg):
        nonlocal april_tags
        april_tags = AprilTags.FromString(msg.data)

    await nt.subscribe("apriltag/tag", cb=on_message)

    image_id = 0
    while True:
        image_id += 1

        ret, frame = cap.read()
        if not ret:
            continue

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        msg = ImageMessage(
            image=frame_gray.tobytes(),
            camera_name="left",
            is_gray=True,
            id=image_id,
        )

        await nt.publish("apriltag/camera", msg.SerializeToString())

        if april_tags is not None and frame is not None:
            if april_tags.tags:
                for tag in april_tags.tags:
                    if tag.corners is not None:
                        corners = [tuple(map(int, corner)) for corner in tag.corners]

                        cv2.polylines(
                            frame,
                            [np.array(corners, dtype=np.int32)],
                            isClosed=True,
                            color=(0, 255, 0),
                            thickness=4,
                        )

                        cv2.putText(
                            frame,
                            f"ID: {tag.tag_id}",
                            (corners[0][0], corners[0][1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 0, 255),
                            3,
                        )

            do_new = True
            april_tags = None

        cv2.imshow("frame", frame)
        cv2.waitKey(1)


if __name__ == "__main__":
    asyncio.run(main())
