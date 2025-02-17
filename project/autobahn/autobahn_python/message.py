# Structure of the message:
# [flag] [length] [topic] [length] [payload]
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import json
import struct


class MessageType(Enum):
    TOPIC_LIST = b"t"
    PUBLISH = b"p"
    SUBSCRIBE = b"s"


@dataclass
class Message(ABC):
    @abstractmethod
    def to_bytes(self) -> bytes:
        pass

    @staticmethod
    def from_bytes(bytes: bytes | str) -> "Message":
        if isinstance(bytes, str):
            bytes = bytes.encode()

        first_byte = bytes[0:1]

        match first_byte:
            case MessageType.TOPIC_LIST.value:
                return MessageTopicList.from_bytes(bytes)
            case MessageType.SUBSCRIBE.value:
                return MessageSubscribe.from_bytes(bytes)
            case MessageType.PUBLISH.value:
                return MessagePublish.from_bytes(bytes)
            case _:
                raise ValueError(f"Unknown message type: {first_byte}")


@dataclass
class MessagePublish(Message):
    topic: str
    id: int
    payload: bytes

    @staticmethod
    def from_bytes(bytes: bytes) -> "MessagePublish":
        assert bytes[0:1] == MessageType.PUBLISH.value
        (topic_len,) = struct.unpack(">B", bytes[1:2])
        topic = bytes[2 : 2 + topic_len].decode()
        (id,) = struct.unpack(">I", bytes[2 + topic_len : 2 + topic_len + 4])
        payload = bytes[2 + topic_len + 4 :]
        return MessagePublish(topic=topic, id=id, payload=payload)

    def to_bytes(self) -> bytes:
        topic_bytes = self.topic.encode()
        return (
            MessageType.PUBLISH.value
            + struct.pack(">B", len(topic_bytes))
            + topic_bytes
            + struct.pack(">I", self.id)
            + self.payload
        )


@dataclass
class MessageSubscribe(Message):
    topic: str
    id: int

    @staticmethod
    def from_bytes(bytes: bytes) -> "MessageSubscribe":
        assert bytes[0:1] == MessageType.SUBSCRIBE.value
        data = json.loads(bytes[1:])
        return MessageSubscribe(topic=data["topic"], id=data["id"])

    def to_bytes(self) -> bytes:
        data = MessageType.SUBSCRIBE.value
        data += json.dumps({"topic": self.topic, "id": self.id}).encode()
        return data


@dataclass
class MessageTopicList(Message):
    topics: list[str]
    id: int

    @staticmethod
    def from_bytes(bytes: bytes) -> "MessageTopicList":
        assert bytes[0:1] == MessageType.TOPIC_LIST.value
        data = json.loads(bytes[1:])
        return MessageTopicList(topics=data["topics"], id=data["id"])

    def to_bytes(self) -> bytes:
        data = MessageType.TOPIC_LIST.value
        data += json.dumps({"topics": self.topics, "id": self.id}).encode()
        return data
