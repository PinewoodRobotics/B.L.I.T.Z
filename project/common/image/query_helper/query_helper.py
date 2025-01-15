import queue
from typing import Callable, Awaitable
from nats.aio.client import Client
import numpy as np
from nats.aio.msg import Msg
import asyncio


class QueryHelper:
    def __init__(
        self,
        input_topic: str,
        output_topic: str,
        nats_client: Client,
        on_message: Callable[[Msg], Awaitable[None]],
    ):
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.queue = asyncio.Queue()
        self.nats_client = nats_client
        self.on_message = on_message

    async def begin_subscribe(self):
        await self.nats_client.subscribe(self.input_topic, cb=self.on_message)

    async def send_message(self, message: bytes):
        await self.nats_client.publish(self.output_topic, message)
        await self.nats_client.flush()
