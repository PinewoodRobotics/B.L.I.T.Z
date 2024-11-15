import asyncio

import cv2
import nats
import numpy as np

from common import profiler
from common.config_class.profiler import ProfilerConfig
from common.msg.image import ImageMessage


async def main():
    cap = cv2.VideoCapture(0)
    nt = await nats.connect("nats://localhost:4222")
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

    while True:
        _, frame = cap.read()
        msg = ImageMessage(
            image=frame,
            camera_name="left",
            is_gray=False,
        )

        await nt.publish("apriltag/camera", msg.serialize())


if __name__ == "__main__":
    asyncio.run(main())
