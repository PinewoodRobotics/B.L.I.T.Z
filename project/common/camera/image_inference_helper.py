import asyncio
import time
from typing import Tuple
from nats.aio.client import Client
from nats.aio.msg import Msg
from project.generated.project.common.proto.Image_pb2 import ImageMessage
from project.generated.project.common.proto.Inference_pb2 import InferenceList
from cv2.typing import MatLike


class ImageInferenceHelper:
    def __init__(
        self, nats_client: Client, image_publish_topic: str, image_subscribe_topic: str
    ):
        self.nats_client = nats_client
        self.queue = asyncio.Queue()
        self.image_id_map = {}
        self.image_pub_topic = image_publish_topic
        self.image_sub_topic = image_subscribe_topic

    async def __on_message(self, msg: Msg):
        await self.queue.put(InferenceList.FromString(msg.data))

    async def start_subscribe(self):
        await self.nats_client.subscribe(self.image_sub_topic, cb=self.__on_message)

    async def send_image_message(self, image: ImageMessage, frame: MatLike):
        await self.nats_client.publish(self.image_pub_topic, image.SerializeToString())
        await self.nats_client.flush()
        self.image_id_map[image.image_id] = {"frame": frame, "timestamp": time.time()}

    async def get_latest_inference(self) -> InferenceList:
        while self.queue.qsize() > 1:  # Skip older messages
            await self.queue.get()

        response = await self.queue.get()
        print(self.queue.qsize())
        return response
