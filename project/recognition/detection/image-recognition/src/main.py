import asyncio
import os
import threading
import time
from typing import Any

import nats
import numpy as np
from nats.aio.client import Client
from nats.aio.msg import Msg
from ultralytics import YOLO
from ultralytics.engine.results import Results

from project.common import profiler
from project.common.config import Config, Module
from project.common.config_class.profiler import ProfilerConfig
from project.common.image.image_util import from_proto_to_cv2
from project.generated.project.common.proto.Image_pb2 import ImageMessage
from project.generated.project.common.proto.Inference_pb2 import Inference
from project.generated.project.common.proto.Inference_pb2 import InferenceList

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"


def input_thread(config: Config) -> None:
    global user_input
    while True:
        user_input = input()
        if user_input == "reload":
            config.reload()


def get_model(config: Config) -> YOLO:
    model = YOLO(config.image_recognition.model)
    if config.image_recognition.device:
        model.to(config.image_recognition.device)
    return model


def from_detection_to_proto(detection: Any, model: YOLO) -> Inference:
    return Inference(
        confidence=float(detection.conf[0].item()),
        class_name=model.names[int(detection.cls[0].item())],
        class_id=int(detection.cls[0].item()),
        bounding_box=detection.xyxy[0].tolist(),
    )


async def main() -> None:
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

    config = Config(
        "config.toml",
        exclude=[
            Module.CAMERA_FEED_CLEANER,
            Module.APRIL_DETECTION,
            Module.PROFILER,
        ],
    )

    thread = threading.Thread(target=input_thread, daemon=True, args=(config,))
    thread.start()

    model = get_model(config)
    nt: Client = await nats.connect(f"nats://localhost:{config.autobahn.port}")

    count = 0
    time_start = time.time()

    async def on_message(msg: Msg) -> None:
        nonlocal count, time_start
        count += 1
        if count >= 10:
            time_end = time.time()
            print(f"Time taken: {count / (time_end - time_start):.2f} QPS")
            time_start = time_end
            count = 0

        msg_decoded = ImageMessage.FromString(msg.data)
        image = from_proto_to_cv2(msg_decoded)

        results: list[Results] = model.predict(source=image)

        inferences = []
        for i in results:
            # Check if `i.boxes` exists and has valid detections
            if i.boxes is None or len(i.boxes) == 0:
                continue

            # Ensure all required attributes have valid data
            if (
                i.boxes.conf is not None
                and len(i.boxes.conf) > 0
                and i.boxes.cls is not None
                and len(i.boxes.cls) > 0
                and i.boxes.xyxy is not None
                and len(i.boxes.xyxy) > 0
            ):
                inferences.append(
                    Inference(
                        confidence=float(i.boxes.conf[0].item()),
                        class_name=model.names[int(i.boxes.cls[0].item())],
                        class_id=int(i.boxes.cls[0].item()),
                        bounding_box=i.boxes.xyxy[0].tolist(),
                    )
                )

        output = InferenceList(
            camera_name=msg_decoded.camera_name,
            inferences=inferences,
        )

        await nt.publish(
            config.image_recognition.image_output_topic,
            output.SerializeToString(),
        )

    await nt.subscribe(
        config.image_recognition.image_input_topic,
        cb=on_message,
    )

    print(config.image_recognition.image_input_topic)

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
