import queue
from typing import Callable, Awaitable
from nats.aio.client import Client
import numpy as np
from nats.aio.msg import Msg
import asyncio

from project.autobahn.autobahn_python.autobahn import Autobahn


class QueryHelper:
    def __init__(
        self,
        input_topic: str,
        output_topic: str,
        autobahn_server: Autobahn,
        on_message: Callable[[bytes], Awaitable[None]],
    ):
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.queue = asyncio.Queue()
        self.autobahn_server = autobahn_server
        self.on_message = on_message

    async def begin_subscribe(self):
        await self.autobahn_server.subscribe(self.input_topic, self.on_message)

    async def send_message(self, message: bytes):
        await self.autobahn_server.publish(self.output_topic, message)
