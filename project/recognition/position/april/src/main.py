import asyncio
import threading
import time
import nats
import numpy as np
import pyapriltags
from nats.aio.msg import Msg
from pyinstrument import Profiler

from project.common.config import Config, Module
from project.common.config_class.profiler import ProfilerConfig
from project.generated.project.common.proto.AprilTag_pb2 import AprilTags, Tag
from project.generated.project.common.proto.Image_pb2 import ImageMessage
import msgpack_numpy as m
from project.common.image.image_util import from_proto_to_cv2
from util import from_detection_to_proto


def get_detector(config: Config):
    return pyapriltags.Detector(
        families=str(config.april_detection.family),
        nthreads=config.april_detection.nthreads,
        quad_decimate=config.april_detection.quad_decimate,
        quad_sigma=config.april_detection.quad_sigma,
        refine_edges=config.april_detection.refine_edges,
        decode_sharpening=config.april_detection.decode_sharpening,
        debug=0,
    )


def input_thread(config: Config):
    global user_input
    while True:
        user_input = input()
        if user_input == "reload":
            config.reload()


async def main():
    config = Config(
        "config.toml",
        exclude=[
            Module.CAMERA_FEED_CLEANER,
            Module.IMAGE_RECOGNITION,
            Module.PROFILER,
        ],
    )
    thread = threading.Thread(target=input_thread, daemon=True, args=(config,))
    thread.start()
    detector = get_detector(config)
    nt = await nats.connect(f"nats://localhost:{config.autobahn.port}")

    count = 0
    time_start = time.time()

    async def on_message(msg: Msg):
        nonlocal count, time_start
        count += 1
        if count >= 10:
            time_end = time.time()
            print(f"Time taken: {count / (time_end - time_start):.2f} QPS")
            time_start = time_end
            count = 0

        msg_decoded = ImageMessage.FromString(msg.data)
        # print(int(time.time() * 1000) - msg_decoded.timestamp)
        image = from_proto_to_cv2(msg_decoded)

        tags = detector.detect(
            image,
            estimate_tag_pose=True,
            camera_params=(
                config.april_detection.cameras[msg_decoded.camera_name].focal_length_x,
                config.april_detection.cameras[msg_decoded.camera_name].focal_length_y,
                config.april_detection.cameras[msg_decoded.camera_name].center_x,
                config.april_detection.cameras[msg_decoded.camera_name].center_y,
            ),
            tag_size=config.april_detection.tag_size,
        )

        output = AprilTags(
            camera_name=msg_decoded.camera_name,
            image_id=msg_decoded.id,
            tags=[from_detection_to_proto(tag) for tag in tags],
            timestamp=msg_decoded.timestamp,
        )

        await nt.publish(
            config.april_detection.message.post_camera_output_topic,
            output.SerializeToString(),
        )

    await nt.subscribe(
        config.april_detection.message.post_camera_input_topic,
        cb=on_message,
    )

    print(config.april_detection.message.post_camera_input_topic)

    try:
        await asyncio.Event().wait()  # Wait indefinitely without consuming CPU
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
