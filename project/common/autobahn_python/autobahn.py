from typing import Awaitable, Callable
import websockets
from generated.autobahn.message_pb2 import MessageType, PublishMessage, TopicMessage
import asyncio

from project.common.autobahn_python.util import Address


class Autobahn:
    def __init__(self, address: Address):
        self.address = address
        self.websocket: websockets.ClientConnection | None = None
        self.first_subscription = True
        self.callbacks = {}

    async def begin(self):
        try:
            self.websocket = await websockets.connect(self.address.make_url())
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to WebSocket at {self.address}: {str(e)}"
            )

    async def ping(self):
        if self.websocket is None:
            raise ConnectionError("WebSocket not connected. Call begin() first.")

        await self.websocket.ping()

    async def publish(self, topic: str, payload: bytes):
        if self.websocket is None:
            raise ConnectionError("WebSocket not connected. Call begin() first.")

        message_proto = PublishMessage(
            message_type=MessageType.PUBLISH,
            topic=topic,
            payload=payload,
        )
        await self.websocket.send(message_proto.SerializeToString())

    async def __listener(self):
        while self.websocket is not None:
            try:
                message = await self.websocket.recv()
                if isinstance(message, str):
                    continue

                message_proto = PublishMessage.FromString(message)
                if message_proto.message_type == MessageType.PUBLISH:
                    if message_proto.topic in self.callbacks:
                        await self.callbacks[message_proto.topic](message_proto.payload)
            except Exception as e:
                print(f"Error in listener: {str(e)}")
                break

    async def subscribe(self, topic: str, callback: Callable[[bytes], Awaitable[None]]):
        if self.websocket is None:
            raise ConnectionError("WebSocket not connected. Call begin() first.")

        self.callbacks[topic] = callback
        await self.websocket.send(
            TopicMessage(
                message_type=MessageType.SUBSCRIBE, topic=topic
            ).SerializeToString()
        )

        if self.first_subscription:
            asyncio.create_task(self.__listener())
            self.first_subscription = False
