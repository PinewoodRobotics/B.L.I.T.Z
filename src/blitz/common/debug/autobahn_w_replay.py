import asyncio
import time
from typing import Callable, Awaitable, Any, Dict, Literal, Optional, Union
from autobahn_client.client import Autobahn
from blitz.common.debug.replay_recorder import (
    init_replay_recorder,
    get_next_replay,
    Replay,
)
import threading


class ReplayAutobahn(Autobahn):
    """
    The usual Autobahn class but that is used ONLY TO REPLAY THE REPLAYS.
    """

    def __init__(self, replay_path: str | Literal["latest"] = "latest"):
        self.replay_path = replay_path
        self._callbacks: Dict[str, Callable[[bytes], Awaitable[None]]] = {}
        self._replay_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._replay_started = False
        init_replay_recorder(replay_path, mode="r")

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
        pass

    async def begin(self) -> None:
        pass

    def _replay_loop(self):
        first_timestamp = 0
        last_timestamp = 0
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
                sleep_time = replay.time - last_timestamp
                if sleep_time > 0:
                    time.sleep(sleep_time)
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
