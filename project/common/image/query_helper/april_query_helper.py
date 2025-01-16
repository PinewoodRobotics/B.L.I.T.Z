import random
import time
from typing import List, Tuple
import cv2
import numpy as np
from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.debug.profiler import profile_function
from project.common.image.query_helper.query_helper import QueryHelper
from nats.aio.client import Client
from nats.aio.msg import Msg

from project.generated.project.common.proto.AprilTag_pb2 import AprilTags
from project.generated.project.common.proto.Image_pb2 import ImageMessage


class AprilQueryHelper(QueryHelper):
    def __init__(self, autobahn_server: Autobahn, input_topic: str, output_topic: str):
        super().__init__(
            input_topic=input_topic,
            output_topic=output_topic,
            autobahn_server=autobahn_server,
            on_message=self.__on_message,
        )
        self.image_inference_map = {}

    @profile_function
    async def send_image(self, image: np.ndarray, camera_name: str):
        id = random.randint(0, 1000000)
        timestamp = int(time.time())
        _, compressed_image = cv2.imencode(".jpg", image)
        image_message = ImageMessage(
            image_id=id,
            image=compressed_image.tobytes(),
            camera_name=camera_name,
            timestamp=timestamp,
            height=image.shape[0],
            width=image.shape[1],
            is_gray=True,
        )
        self.image_inference_map[id] = image

        await self.send_message(image_message.SerializeToString())
        return id

    async def __on_message(self, msg: bytes):
        april_tags = AprilTags()
        april_tags.ParseFromString(msg)
        await self.queue.put(april_tags)

    async def send_bulk_images(self, images: List[Tuple[np.ndarray, str]]):
        ids = []
        for image, camera_name in images:
            id = await self.send_image(image, camera_name)
            ids.append(id)
            self.image_inference_map[id] = image

        return ids

    async def send_and_wait_for_response(self, image: np.ndarray, camera_name: str):
        id = await self.send_image(image, camera_name)
        response: AprilTags = await self.queue.get()
        while response.image_id != id:
            response = await self.queue.get()

        print(f"Time taken: {(time.time() - response.timestamp) * 1000:.2f} ms")
        return response

    async def send_and_wait_bulk_images(self, images: List[Tuple[np.ndarray, str]]):
        ids = await self.send_bulk_images(images)
        responses: list[AprilTags] = []
        response: AprilTags
        while len(ids) != 0:
            response = await self.queue.get()
            if response.image_id in ids:
                responses.append(response)
                ids.remove(response.image_id)

        print(responses)
        return responses

    async def get_image(self, id: int):
        return self.image_inference_map[id]
