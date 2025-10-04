import os
from backend.python.common.debug.replay_recorder import (
    GLOBAL_INSTANCE,
    Recorder,
    Player,
    close,
    get_next_key_replay,
    get_next_replay,
    init_replay_recorder,
    record_output,
)
from backend.generated.proto.python.replay.replay_pb2 import Replay


def read_file_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def write_file_bytes(path: str, data: bytes):
    with open(path, "wb") as f:
        f.write(data)


def read_first_line_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.readline()


def add_sample_replay_data(additional: dict[str, str] = {}):
    recorder = Recorder("test")
    recorder.record_output("test", "test")
    for key, value in additional.items():
        recorder.record_output(key, value)
    recorder.close()


def test_replay_recorder():
    add_sample_replay_data()


def test_global_replay_player():
    add_sample_replay_data()
    player = Player("test")
    most_recent_replay = player.get_next_replay()
    assert most_recent_replay is not None
    assert most_recent_replay.key == "test"
    assert most_recent_replay.data_type == "str"
    assert most_recent_replay.data == b"test"
    assert most_recent_replay.time is not None
    assert player.get_next_replay() is None


def test_key_replay_player():
    add_sample_replay_data({"test2": "test2"})
    player = Player("test")
    most_recent_replay = player.get_next_key_replay("test")
    assert most_recent_replay is not None
    assert most_recent_replay.key == "test"
    assert most_recent_replay.data_type == "str"
    assert most_recent_replay.data == b"test"
    assert player.get_next_key_replay("test2") is not None
    assert player.get_next_key_replay("test2") is None
    assert player.get_next_key_replay("test") is None


def test_key_global_replay_player():
    add_sample_replay_data({"test2": "test2"})
    player = Player("test")
    most_recent_replay = player.get_next_replay()

    assert most_recent_replay is not None
    assert most_recent_replay.key == "test"
    assert most_recent_replay.data_type == "str"
    assert most_recent_replay.data == b"test"

    next_replay = player.get_next_replay()
    assert next_replay is not None
    assert next_replay.key == "test2"
    assert next_replay.data_type == "str"
    assert next_replay.data == b"test2"

    assert player.get_next_key_replay("test") is not None

    assert player.get_next_replay() is None


def test_replay_api(tmp_path):
    replay_dir = tmp_path
    replay_path = os.path.join(replay_dir, "replay-test.db")

    path = init_replay_recorder(replay_path, mode="w")
    assert os.path.exists(path)

    record_output("foo", "bar")
    record_output("baz", "qux")
    record_output("num", 123)
    record_output("flt", 3.14)

    close()
    init_replay_recorder(replay_path, mode="r")
    assert os.path.exists(replay_path)

    replay1 = get_next_replay()
    assert isinstance(replay1, Replay)
    assert replay1.key in {"foo", "baz", "num", "flt"}
    assert replay1.data is not None

    replay2 = get_next_key_replay("foo")
    assert isinstance(replay2, Replay)
    assert replay2.key == "foo"
    assert replay2.data == b"bar"

    assert get_next_key_replay("foo") is None

    while get_next_replay() is not None:
        pass
    assert get_next_replay() is None

    # Clean up
    close()


def test_replay_latest():
    init_replay_recorder(mode="w")
    record_output("test", "test")
    close()

    init_replay_recorder("latest", mode="r")
    current_replay = get_next_replay()
    assert current_replay is not None
    assert current_replay.key == "test"
    assert current_replay.data == b"test"
    close()
