from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import cast

from autobahn_client.client import Autobahn

from watchdog.generated.PiStatus_pb2 import Ping, Pong
from watchdog.helper import setup_ping_pong


class FakeAutobahn:
    def __init__(self) -> None:
        self.subscriptions: dict[str, Callable[[bytes], Awaitable[None]]] = {}
        self.publications: list[tuple[str, bytes]] = []

    async def subscribe(
        self, topic: str, callback: Callable[[bytes], Awaitable[None]]
    ) -> None:
        self.subscriptions[topic] = callback

    async def publish(self, topic: str, payload: bytes) -> None:
        self.publications.append((topic, payload))


def test_ping_topic_publishes_pong_with_system_name_and_original_timestamp() -> None:
    autobahn = FakeAutobahn()

    async def exercise_ping() -> None:
        await setup_ping_pong(cast(Autobahn, cast(object, autobahn)), "test-pi")
        await autobahn.subscriptions["pi-ping"](Ping(timestamp=12345).SerializeToString())

    asyncio.run(exercise_ping())

    assert len(autobahn.publications) == 1
    topic, payload = autobahn.publications[0]
    pong = Pong.FromString(payload)
    assert topic == "pi-pong"
    assert pong.pi_name == "test-pi"
    assert pong.timestamp_ms_original == 12345
    assert pong.timestamp_ms_received > 0
