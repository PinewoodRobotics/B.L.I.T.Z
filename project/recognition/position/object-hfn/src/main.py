import asyncio
import time
import cv2
import nats
import numpy as np
from nats.aio.msg import Msg
import nest_asyncio
import random
from asyncio import CancelledError

from project.common.camera.image_inference_helper import ImageInferenceHelper
from project.generated.project.common.proto.Inference_pb2 import InferenceList
from project.common import profiler
from project.common.config_class.profiler import ProfilerConfig
from project.generated.project.common.proto.Image_pb2 import ImageMessage
from project.generated.project.common.proto.Inference_pb2 import Inference


def render_detections(frame: np.ndarray, inference: Inference):
    for i in range(0, len(inference.bounding_box), 4):
        box = inference.bounding_box[i : i + 4]
        x1, y1, x2, y2 = map(int, box)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=2)

        # Add label with confidence
        label = f"{inference.class_name}: {inference.confidence:.2f}"
        cv2.putText(
            frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
        )


async def main():
    cap = cv2.VideoCapture(0)
    nt = await nats.connect("nats://localhost:4222")
    image_inference_helper = ImageInferenceHelper(
        nt, "recognition/image_input", "recognition/image_output"
    )
    await image_inference_helper.start_subscribe()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            _, compressed_image = cv2.imencode(".jpg", frame)

            image_id = random.randint(0, 1000000)

            msg = ImageMessage(
                image=compressed_image.tobytes(),
                camera_name="camera0",
                is_gray=False,
                id=image_id,
                height=frame.shape[0],
                width=frame.shape[1],
                timestamp=int(time.time() * 1000),
            )

            await image_inference_helper.send_image_message(msg, frame)

            inference = await image_inference_helper.get_latest_inference()
            for inference in inference.inferences:
                render_detections(frame, inference)

            cv2.imshow("frame", frame)
            cv2.waitKey(1)
    except KeyboardInterrupt as e:
        print("Exiting...")
    except CancelledError as e:
        print("Exiting...")
    finally:
        cap.release()
        cv2.destroyAllWindows()


asyncio.run(main())
