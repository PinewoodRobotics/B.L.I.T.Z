import asyncio
from backend.python.common.debug.pubsub_replay import autolog
from backend.python.common.debug.replay_recorder import (
    close,
    get_next_replay,
    init_replay_recorder,
)


def test_autolog():
    init_replay_recorder("test.db", mode="w")

    @autolog("test")
    async def test_func(data: bytes):
        return data

    async def run_async():
        await test_func(b"test")
        await test_func(b"test2")

    asyncio.run(run_async())

    close()

    init_replay_recorder("test.db", mode="r")

    first = get_next_replay()
    second = get_next_replay()
    assert first is not None
    assert first.key == "test"
    assert first.data == b"test"
    assert second is not None
    assert second.key == "test"
    assert second.data == b"test2"

    assert get_next_replay() is None

    close()
