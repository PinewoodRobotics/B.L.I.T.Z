from enum import Enum
import io
from struct import Struct
from typing import Awaitable, Callable
import websockets
from websockets.server import ServerConnection
import asyncio

# Structure of the message:
# [flag] [length] [topic] [length] [payload]


class Flags(Enum):
    SUBSCRIBE = b"\x01"  # flag: 0x01
    UNSUBSCRIBE = b"\x02"  # flag: 0x02
    PUBLISH = b"\x03"  # flag: 0x03


class Autobahn:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.websocket = None
        self.subscriptions = {}

    async def begin(self):
        self.websocket = await websockets.connect(f"ws://{self.host}:{self.port}")
        asyncio.create_task(self._listen())

    async def subscribe(self, topic: str, callback: Callable[[bytes], Awaitable[None]]):
        self.subscriptions[topic] = callback
        await self.__publish(Flags.SUBSCRIBE, topic.encode(), b"")

    async def unsubscribe(self, topic: str):
        del self.subscriptions[topic]
        await self.__publish(Flags.UNSUBSCRIBE, topic.encode(), b"")

    async def _listen(self):
        try:
            while True:
                try:
                    if self.websocket:
                        # Receive the message
                        msg = await self.websocket.recv()

                        # Ensure msg is bytes
                        if isinstance(msg, str):
                            msg = msg.encode("utf-8")

                        reader = io.BytesIO(msg)

                        _ = int.from_bytes(reader.read(1), byteorder="big")
                        topic_length = int.from_bytes(reader.read(2), byteorder="big")
                        topic = reader.read(topic_length).decode("utf-8")
                        payload = reader.read()

                        for subscription_topic, callback in self.subscriptions.items():
                            if topic.startswith(subscription_topic):
                                await callback(payload)
                except websockets.exceptions.ConnectionClosed:
                    break
        except Exception as e:
            print(f"Error in listener: {e}")

    async def __publish(self, flag: Flags, topic: bytes, message: bytes):
        if self.websocket:
            try:
                await self.websocket.send(
                    flag.value
                    + len(topic).to_bytes(2, "big")
                    + topic
                    + len(message).to_bytes(2, "big")
                    + message
                )
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")

    async def publish(self, topic: str, message: bytes):
        await self.__publish(Flags.PUBLISH, topic.encode(), message)
