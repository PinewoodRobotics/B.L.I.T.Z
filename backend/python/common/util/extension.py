from typing import Awaitable, Callable
from autobahn_client import Autobahn


async def subscribe_to_multiple_topics(
    self: Autobahn,
    topics: list[str],
    callback: Callable[[bytes], Awaitable[None]],
) -> None:
    # TODO: add this to the autobahn client library itself.
    for topic in topics:
        await self.subscribe(topic, callback)
