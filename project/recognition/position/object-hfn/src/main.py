import asyncio
import time
import cv2
import nats
import numpy as np
import random
from asyncio import CancelledError

from project.common.camera.box_frustum_conversion import (
    bbox_to_frustum,
)
from project.common.camera.image_inference_helper import ImageInferenceHelper
from project.common.camera.transform import unfisheye_image
from generated.Image_pb2 import ImageMessage
from generated.Inference_pb2 import Inference
from lidar_frustum import LidarPointsFrustum, Point3D

camera_matrix = np.array(
    [
        [1487.1124346674526, 0.0, 945.122412363984],
        [0.0, 1434.705975660968, 547.8805261625706],
        [0.0, 0.0, 1.0],
    ]
)

dist_coef = np.array(
    [
        -0.4513475113205368,
        0.21139658631382788,
        -0.0028846973373456855,
        0.0021349747481580624,
        -0.055584296827295585,
    ]
)

camera_position = []


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
    lidar_frustum = LidarPointsFrustum(8080)
    image_inference_helper = ImageInferenceHelper(
        nt, "recognition/image_input", "recognition/image_output"
    )
    await image_inference_helper.start_subscribe()

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                continue

            unfisheyed_image = unfisheye_image(frame, camera_matrix, dist_coef)

            _, compressed_image = cv2.imencode(".jpg", frame)

            image_id = random.randint(0, 1000000)

            msg = ImageMessage(
                image=compressed_image.tobytes(),
                camera_name="camera0",
                is_gray=False,
                image_id=image_id,
                height=frame.shape[0],
                width=frame.shape[1],
                timestamp=int(time.time() * 1000),
            )

            await image_inference_helper.send_image_message(msg, frame)

            inference = await image_inference_helper.get_latest_inference()
            for inference in inference.inferences:
                transformed_frustum = bbox_to_frustum(
                    camera_matrix, inference.bounding_box, 5
                )
                res = lidar_frustum.get_frustum_points(
                    Point3D(-0.012, 0, 0),
                    [Point3D(pt[0], pt[1], pt[2]) for pt in transformed_frustum],
                )
                if res is None:
                    print("Womp Womp")
                else:
                    avg_total_distance = 0

                    for i in res:
                        avg_total_distance = avg_total_distance + np.sqrt(
                            i.x * i.x + i.y * i.y + i.z * i.z
                        )
                    print(len(res))
                    print(str(avg_total_distance / len(res)))
                render_detections(frame, inference)

            cv2.imshow("frame", unfisheyed_image)
            cv2.waitKey(1)
    except KeyboardInterrupt:
        print("Exiting...")
    except CancelledError:
        print("Exiting...")
    finally:
        cap.release()
        cv2.destroyAllWindows()


asyncio.run(main())
