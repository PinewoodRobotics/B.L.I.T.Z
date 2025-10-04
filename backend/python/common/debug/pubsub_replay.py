import asyncio
import time
from typing import Callable, Awaitable, Any, Dict, Literal, Optional, Union
from autobahn_client import Address
from autobahn_client.client import Autobahn
from backend.python.common.debug.replay_recorder import (
    init_replay_recorder,
    get_next_replay,
    Replay,
    record_output,
)
import threading

from functools import wraps
from typing import Callable, Awaitable, Any, TypeVar, overload, Union, cast


def autolog(*topics: str, do_record: bool = True):
    """
    Decorator to modify a function for autolog subscription.
    Usage:
        @autolog("topic")
        async def func(data: bytes): ...
    or:
        @autolog(["topic1", "topic2"])
        async def func(data: bytes): ...
    """

    def decorator(
        func: Callable[[bytes], Awaitable[Any]],
    ) -> Callable[[bytes], Awaitable[Any]]:
        @wraps(func)
        async def wrapper(data: bytes):
            result = await func(data)
            if do_record:
                for topic in topics:
                    record_output(topic, data)

            return result

        return wrapper

    return decorator


class ReplayAutobahn(Autobahn):
    """
    The usual Autobahn class but that is used ONLY TO REPLAY THE REPLAYS.
    """

    def __init__(
        self,
        replay_path: str | Literal["latest"] = "latest",
        publish_on_real_autobahn: bool = False,
        address: Address | None = None,
    ):
        self.replay_path = replay_path
        self._callbacks: Dict[str, Callable[[bytes], Awaitable[None]]] = {}
        self._replay_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._replay_started = False
        self._publish_on_real_autobahn = publish_on_real_autobahn
        self._address = address

        if address is not None:
            super().__init__(address)

    async def subscribe(
        self, topic: str, callback: Callable[[bytes], Awaitable[None]]
    ) -> None:
        self._callbacks[topic] = callback
        if not self._replay_started:
            self._replay_started = True
            self._loop = asyncio.get_running_loop()
            self._replay_thread = threading.Thread(
                target=self._replay_loop, daemon=True
            )
            self._replay_thread.start()

    async def unsubscribe(self, topic: str) -> None:
        if topic in self._callbacks:
            del self._callbacks[topic]

    async def publish(self, topic: str, payload: bytes) -> None:
        if self._publish_on_real_autobahn:
            await super().publish(topic, payload)

    async def begin(self) -> None:
        if self._publish_on_real_autobahn:
            await super().begin()

    def _replay_loop(self):
        first_timestamp = None
        last_timestamp = None
        while not self._stop_event.is_set():
            try:
                replay = get_next_replay()
            except Exception:
                break
            if replay is None:
                break

            topic = replay.key
            payload = replay.data

            if first_timestamp is None:
                first_timestamp = replay.time
                last_timestamp = replay.time
            else:
                assert last_timestamp is not None

                sleep_time = replay.time - last_timestamp

                if 0 < sleep_time < 10:
                    time.sleep(sleep_time)
                else:
                    time.sleep(0.025)

                last_timestamp = replay.time

            if topic in self._callbacks and self._loop is not None:
                cb = self._callbacks[topic]
                coro = cb(payload)
                if not asyncio.iscoroutine(coro):
                    raise TypeError("Callback must be a coroutine function")
                asyncio.run_coroutine_threadsafe(coro, self._loop)

    def close(self):
        self._stop_event.set()
        if self._replay_thread is not None:
            self._replay_thread.join()
        self._callbacks.clear()
        self._replay_started = False
        self._loop = None
        self._replay_thread = None
