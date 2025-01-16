from enum import Enum
from typing import Awaitable, Callable
import websockets
from websockets.server import ServerConnection
import asyncio


class Flags(Enum):
    SUBSCRIBE = "SUBSCRIBE"
    UNSUBSCRIBE = "UNSUBSCRIBE"


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
        await self.publish(Flags.SUBSCRIBE.value, topic.encode())

    async def unsubscribe(self, topic: str):
        del self.subscriptions[topic]
        await self.publish(Flags.UNSUBSCRIBE.value, topic.encode())

    async def _listen(self):
        print("Listening for messages")
        try:
            while True:
                try:
                    if self.websocket:
                        msg = await self.websocket.recv()
                        for topic, callback in self.subscriptions.items():
                            if msg.startswith(topic.encode()):
                                await callback(msg[len(topic) :])
                except websockets.exceptions.ConnectionClosed:
                    break
        except Exception as e:
            print(f"Error in listener: {e}")

    async def publish(self, topic: str, message: bytes):
        if self.websocket:
            try:
                await self.websocket.send(topic.encode() + message)
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
