from collections import defaultdict
from dataclasses import dataclass
import random
from project.autobahn.autobahn_python.message import (
    Message,
    MessagePublish,
    MessageSubscribe,
    MessageTopicList,
)
from typing import Awaitable, Callable
import websockets
import asyncio

from project.common.debug.logger import debug, info, warning, error


@dataclass
class Address:
    host: str
    port: int

    def __str__(self) -> str:
        return f"Host: {self.host}, Port: {self.port}"

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Address):
            return False
        return self.host == value.host and self.port == value.port


class Peer:
    def __init__(self, address: Address):
        self.address = address
        self.topics = set[str]()
        self.websocket = None
        self.id = -1
        debug(f"Started Peer: {str(address)}")

    async def send(self, message: Message):
        debug(f"Sending to peer ({str(self.address)}): {str(message)}")
        await self.ensure_connected()
        assert self.websocket is not None
        await self.websocket.send(message.to_bytes())

    async def maybe_publish(self, topic: str, data: bytes):
        await self.ensure_connected()
        assert self.websocket is not None
        if topic in self.topics:
            await self.websocket.send(data)
        debug(f"Maybe publishing to {str(self.address)}.")

    async def ensure_connected(self):
        if self.websocket:
            return

        self.websocket = await websockets.connect(
            f"ws://{self.address.host}:{self.address.port}"
        )

        raw_msg = await self.websocket.recv()
        debug(f"Received raw message: {raw_msg}")
        debug(f"First byte: {raw_msg[0]}")
        msg = Message.from_bytes(raw_msg)
        assert isinstance(msg, MessageTopicList)
        self.topics = set(msg.topics)
        self.id = msg.id


class Listener:
    def __init__(self, peer_addrs: list[Address], addr: Address):
        self.peers: list[Peer] = [
            Peer(peer_addr) for peer_addr in peer_addrs if peer_addr.port != addr.port
        ]
        self.topics = defaultdict[
            str, set[websockets.ServerConnection | Callable[[bytes], Awaitable[None]]]
        ]()
        self.server = None
        self.addr = addr
        self.id = random.randint(0, 1000000)

    async def handle_client(self, websocket: websockets.ServerConnection):
        info("Got client connection!")
        topic_list = MessageTopicList(list(self.topics), self.id)
        await websocket.send(topic_list.to_bytes())

        try:
            async for message_bytes in websocket:
                info(f"Message from websocket: {message_bytes}")
                message = Message.from_bytes(message_bytes)
                if isinstance(message, MessageSubscribe):
                    await self.__subscribe(message.topic, websocket, message.id)
                elif isinstance(message, MessagePublish):
                    assert isinstance(message_bytes, bytes)
                    await self.__publish(message, message_bytes, message.id)
                else:
                    error("Could not parse!")
        finally:
            for connections in self.topics.values():
                connections.discard(websocket)

    async def run(self):
        self.server = await websockets.serve(
            self.handle_client,
            self.addr.host,
            self.addr.port,
        )
        await self.server.wait_closed()

    async def __publish(
        self,
        message: MessagePublish,
        message_bytes: bytes,
        exclude_id: int | None = None,
    ):
        await asyncio.gather(
            *(
                connection.send(message_bytes)
                for connection in self.topics[message.topic]
                if isinstance(connection, websockets.ServerConnection)
            ),
            *(
                peer.maybe_publish(message.topic, message_bytes)
                for peer in self.peers
                if not peer.id == exclude_id
            ),
            *(
                connection(message.payload)
                for connection in self.topics[message.topic]
                if not isinstance(connection, websockets.ServerConnection)
            ),
        )

    async def __subscribe(
        self,
        topic: str,
        destination: websockets.ServerConnection | Callable[[bytes], Awaitable[None]],
        exclude_id: int | None = None,
    ):
        print(str(topic in self.topics))
        if topic not in self.topics:
            self.topics[topic] = set([destination])
        else:
            self.topics[topic].add(destination)

        topic_list_msg = MessageSubscribe(topic, self.id)
        await asyncio.gather(
            *(
                peer.send(topic_list_msg)
                for peer in self.peers
                if not peer.id == exclude_id
            )
        )

    async def publish(self, topic: str, payload: bytes):
        if topic not in self.topics:
            warning(
                "Failed to send message to topic as it is not inside the topic list."
            )
            return

        message = MessagePublish(topic=topic, payload=payload, id=self.id)
        await self.__publish(message, message.to_bytes())

    async def subscribe(self, topic: str, callback: Callable[[bytes], Awaitable[None]]):
        await self.__subscribe(topic, callback)
