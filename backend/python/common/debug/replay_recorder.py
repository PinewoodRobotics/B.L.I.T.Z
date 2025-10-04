import os
import time
import time as time_module
from typing import Literal, Union
import cv2
import numpy as np

from backend.python.common.camera.image_utils import encode_image
from backend.python.common.debug.logger import error, success, warning
from backend.generated.proto.python.replay.replay_pb2 import Replay
from google.protobuf.message import Message
from peewee import BlobField, FloatField, Model, AutoField, CharField, SqliteDatabase
from typing import TypeVar, Generic

from backend.generated.proto.python.sensor.camera_sensor_pb2 import ImageFormat

# This is a simple replay recorder that records and plays back data. It is designed to use the sqlite database
# to store the data. It is not designed to be used in a multi-process environment.

T = TypeVar("T", bound=Union[np.ndarray, Message, float, int, str, bytes])
Mode = Literal["r", "w"]

GLOBAL_INSTANCE: "iPod | None" = None


class ReplayDB(Model):
    id = AutoField()
    key = CharField()
    timestamp = FloatField()
    data_type = CharField()
    data = BlobField()

    class Meta:
        pass


def init_database(db_path="replay.db", clear: bool = False):
    """Initialize the database with a specific path"""
    db = SqliteDatabase(db_path)
    ReplayDB._meta.database = db  # type: ignore
    db.connect()
    db.create_tables([ReplayDB])
    if clear:
        db.execute_sql("DELETE FROM ReplayDB")

    return db


def close_database():
    """Close the database connection"""
    if hasattr(ReplayDB._meta, "database") and ReplayDB._meta.database:  # type: ignore
        ReplayDB._meta.database.close()  # type: ignore


class iPod:
    def __init__(self, path: str, mode: Mode = "w"):
        self.path = path
        self.mode = mode

        dir_name = os.path.dirname(path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        file_path = path
        if path.endswith(".db"):
            file_path = path
        else:
            file_path = path + ".db"

        if os.path.exists(file_path) and mode == "w":
            warning(f"File {file_path} already exists. Overwriting.")

        self.db = init_database(file_path, mode == "w")

    def get_next_replay(self) -> Replay | None:
        raise NotImplementedError("get_next_replay is not implemented")

    def get_next_key_replay(
        self, key: str, follow_global: bool = False
    ) -> Replay | None:
        raise NotImplementedError("get_next_key_replay is not implemented")

    def record_output(self, key: str, data: T):
        raise NotImplementedError("record_output is not implemented")

    def write(self, key: str, data_type: str, data: bytes, time: float = time.time()):
        raise NotImplementedError("write is not implemented")

    def close(self):
        close_database()


class Recorder(iPod):
    def __init__(self, path: str):
        super().__init__(path, "w")

    def record_output(self, key: str, data: T):
        if isinstance(data, np.ndarray):
            self._record_ndarray(key, data)
        elif isinstance(data, float):
            self._record_float(key, data)
        elif isinstance(data, int):
            self._record_int(key, data)
        elif isinstance(data, str):
            self._record_string(key, data)
        elif isinstance(data, Message):
            self._record_protobuf(key, data)
        elif isinstance(data, bytes):
            self._record_bytes(key, data)
        else:
            error(f"Unsupported data type: {type(data)}")

    def _record_ndarray(self, key: str, data: np.ndarray):
        self.write(key, "ndarray", data.tobytes())

    def _record_protobuf(self, key: str, data: Message):
        self.write(key, "protobuf", data.SerializeToString())

    def _record_float(self, key: str, data: float):
        self.write(key, "float", data.hex().encode("utf-8"))

    def _record_int(self, key: str, data: int):
        self.write(key, "int", data.to_bytes(8, byteorder="little", signed=True))

    def _record_string(self, key: str, data: str):
        self.write(key, "str", data.encode("utf-8"))

    def _record_bytes(self, key: str, data: bytes):
        self.write(key, "bytes", data)

    def write(
        self, key: str, data_type: str, data: bytes, time: float = time_module.time()
    ):
        ReplayDB.create(key=key, timestamp=time, data_type=data_type, data=data)


class Player(iPod):
    def __init__(self, path: str):
        super().__init__(path, "r")
        self._last_id_by_key: dict[str, int] = {}
        self._last_id: int = 0

    def get_next_replay(self) -> Replay | None:
        row = (
            ReplayDB.select()
            .where(ReplayDB.id > self._last_id)  # type: ignore
            .order_by(ReplayDB.id)
            .first()
        )

        if row is None:
            return None

        self._last_id = row.id

        return Replay(
            key=row.key, data_type=row.data_type, time=row.timestamp, data=row.data
        )

    def get_next_key_replay(
        self, key: str, follow_global: bool = False
    ) -> Replay | None:
        last_id = self._last_id_by_key.get(key, 0)
        row = (
            ReplayDB.select()
            .where(
                (ReplayDB.key == key)
                & (ReplayDB.id > last_id)  # type: ignore
                & (ReplayDB.id > self._last_id if follow_global else True)  # type: ignore
            )
            .order_by(ReplayDB.id)
            .first()
        )

        if row is None:
            return None

        self._last_id_by_key[key] = row.id

        return Replay(
            key=row.key, data_type=row.data_type, time=row.timestamp, data=row.data
        )


def find_latest_replay(dir: str) -> str:
    log_files = [
        file
        for file in os.listdir(dir)
        if file.endswith(".db") and file.startswith("replay-")
    ]
    if not log_files:
        raise FileNotFoundError("No replay log files found in the directory.")
    log_files.sort(reverse=True)
    return os.path.join(dir, log_files[0])


def init_replay_recorder(
    replay_path: str | Literal["latest"] = "replay-"
    + time.strftime("%Y-%m-%d_%H-%M-%S")
    + ".db",
    mode: Mode = "w",
    folder_path: str = "replays",
):
    global GLOBAL_INSTANCE
    if replay_path == "latest" and mode == "r":
        replay_path = find_latest_replay(os.path.join(os.getcwd(), folder_path))
    else:
        replay_path = os.path.join(folder_path, replay_path)

    if mode == "w":
        GLOBAL_INSTANCE = Recorder(replay_path)
    else:
        GLOBAL_INSTANCE = Player(replay_path)

    success(f"Initialized replay recorder at {os.path.abspath(replay_path)}")

    return replay_path


def get_next_replay() -> Replay | None:
    global GLOBAL_INSTANCE
    if GLOBAL_INSTANCE is None:
        error("Replay recorder not initialized or in write mode")
        raise RuntimeError("Replay recorder not initialized or in write mode")

    return GLOBAL_INSTANCE.get_next_replay()


def get_next_key_replay(key: str) -> Replay | None:
    global GLOBAL_INSTANCE
    if GLOBAL_INSTANCE is None:
        error("Replay recorder not initialized or in write mode")
        raise RuntimeError("Replay recorder not initialized or in write mode")

    return GLOBAL_INSTANCE.get_next_key_replay(key)


def record_output(key: str, data: T):
    global GLOBAL_INSTANCE
    if GLOBAL_INSTANCE is None:
        error("Replay recorder not initialized or in write mode")
        raise RuntimeError("Replay recorder not initialized or in write mode")

    GLOBAL_INSTANCE.record_output(key, data)


def record_image(
    key: str,
    image: np.ndarray,
    format: ImageFormat = ImageFormat.RGB,
    do_compress: bool = True,
    compression_quality: int = 90,
):
    record_output(key, encode_image(image, format, do_compress, compression_quality))


def close():
    global GLOBAL_INSTANCE
    if GLOBAL_INSTANCE is not None:
        GLOBAL_INSTANCE.close()
        GLOBAL_INSTANCE = None
