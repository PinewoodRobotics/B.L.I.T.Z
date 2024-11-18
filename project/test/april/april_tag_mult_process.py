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

from project.common import profiler
from project.common.config_class.profiler import ProfilerConfig
from project.generated.project.common.proto.AprilTag_pb2 import AprilTags, Tag
from project.generated.project.common.proto.Image_pb2 import ImageMessage


def render_tags(frame: np.ndarray, tags: list[Tag]):
    for tag in tags:
        vertices = []
        for i in range(0, len(tag.corners), 2):
            vertices.append(tuple(map(int, tag.corners[i : i + 2])))

        cv2.polylines(
            frame,
            [np.array(vertices, dtype=np.int32)],
            isClosed=True,
            color=(0, 255, 0),
            thickness=4,
        )


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

    cap = cv2.VideoCapture(0)
    nt = await nats.connect(f"nats://localhost:4222")

    queue = asyncio.Queue()
    image_id_map = {}

    async def on_message(msg: Msg):
        await queue.put(AprilTags.FromString(msg.data))

    await nt.subscribe("apriltag/tag", cb=on_message)

    image_id = 0
    while True:
        image_id += 1

        ret, frame = cap.read()
        if not ret:
            continue

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, compressed_image = cv2.imencode(".jpg", frame_gray)

        msg = ImageMessage(
            image=compressed_image.tobytes(),
            camera_name="left",
            is_gray=True,
            id=image_id,
            height=frame_gray.shape[0],
            width=frame_gray.shape[1],
            timestamp=int(time.time() * 1000),
        )

        image_id_map[image_id] = frame

        await nt.publish("apriltag/camera", msg.SerializeToString())
        await nt.flush()

        if not queue.empty():
            april_tags = await queue.get()
            print(int(time.time() * 1000) - april_tags.timestamp, str(queue.qsize()))
            render_tags(image_id_map[april_tags.image_id], april_tags.tags)
            cv2.imshow("frame", image_id_map[april_tags.image_id])
            cv2.waitKey(1)
            image_id_map.pop(april_tags.image_id)


if __name__ == "__main__":
    asyncio.run(main())
