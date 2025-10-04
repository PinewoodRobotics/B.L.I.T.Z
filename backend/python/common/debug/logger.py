import asyncio
import threading
import time
from typing import Any, Callable, Coroutine
import colorama
from enum import Enum
from functools import wraps

from autobahn_client.client import Autobahn
from backend.python.common.util.system import get_system_name
from backend.generated.proto.python.status.PiStatus_pb2 import LogMessage, StatusType
from backend.generated.proto.python.status.StateLogging_pb2 import (
    DataType,
    StateLogging,
)


SUFFIX_STATS = "/stats"
SUFFIX_AKIT = "/akit"


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

    def get_importance(self):
        return {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
        }[self]

    def __lt__(self, other: "LogLevel"):
        return self.get_importance() < other.get_importance()

    def __le__(self, other: "LogLevel"):
        return self.get_importance() <= other.get_importance()


class LogEventLoop(threading.Thread):
    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        self.is_running = True
        self.start()

    def run(self):
        pass

    def run_coroutine(self, coroutine: Coroutine[Any, Any, Any]):
        asyncio.run_coroutine_threadsafe(coroutine, self.loop)

    def stop(self):
        self.is_running = False
        self.loop.stop()
        self.loop.close()


PREFIX = ""
LOG_LEVEL = LogLevel.DEBUG
autobahn_instance: Autobahn | None = None
STATS_PUBLISH_TOPIC = ""
main_event_loop: LogEventLoop | None = None
SYSTEM_NAME: str | None = None


def stats_for_nerds(print_stats: bool = True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()

            if print_stats:
                info(
                    f"Stats for nerds: {func.__name__} took {(end_time - start_time) * 1000:.2f} ms"
                )

            return result

        return wrapper

    return decorator


def stats_for_nerds_akit(send_stats: bool = True, print_stats: bool = True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            if send_stats:
                log_to_akit(func.__name__, [(end_time - start_time) * 1000])

            if print_stats:
                info(
                    f"Function {func.__name__} took {(end_time - start_time) * 1000}ms to run."
                )

            return result

        return wrapper

    return decorator


def init_logging(
    prefix: str,
    log_level: LogLevel,
    main_event_loop_=LogEventLoop(),
    system_pub_topic: str | None = None,
    autobahn: Autobahn | None = None,
    system_name: str | None = None,
):
    """
    Initialize the logging system with a prefix and log level.

    Args:
        prefix (str): The prefix to prepend to all log messages
        log_level (LogLevel): The minimum log level to display messages for
    """
    global PREFIX
    global LOG_LEVEL
    global STATS_PUBLISH_TOPIC
    global autobahn_instance
    global main_event_loop
    global SYSTEM_NAME

    autobahn_instance = autobahn
    colorama.init()
    PREFIX = prefix  # pyright: ignore[reportConstantRedefinition]
    LOG_LEVEL = log_level  # pyright: ignore[reportConstantRedefinition]
    main_event_loop = main_event_loop_
    SYSTEM_NAME = system_name  # pyright: ignore[reportConstantRedefinition]

    if autobahn_instance:
        if system_pub_topic:
            STATS_PUBLISH_TOPIC = (  # pyright: ignore[reportConstantRedefinition]
                system_pub_topic
            )
        else:
            raise ValueError("System pub topic is required if autobahn is provided")


def set_log_level(log_level: LogLevel):
    global LOG_LEVEL
    LOG_LEVEL = log_level  # pyright: ignore[reportConstantRedefinition]


def message(message: str):
    if LOG_LEVEL <= LogLevel.INFO:
        log(PREFIX, message, colorama.Fore.RESET)


def error(message: str):
    if LOG_LEVEL <= LogLevel.ERROR:
        log(PREFIX, message, colorama.Fore.RED)


def warning(message: str):
    if LOG_LEVEL <= LogLevel.WARNING:
        log(PREFIX, message, colorama.Fore.YELLOW)


def info(message: str):
    if LOG_LEVEL <= LogLevel.INFO:
        log(PREFIX, message, colorama.Fore.CYAN)


def debug(message: str):
    if LOG_LEVEL <= LogLevel.DEBUG:
        log(PREFIX, message, colorama.Fore.BLUE)


def success(message: str):
    if LOG_LEVEL <= LogLevel.INFO:
        log(PREFIX, message, colorama.Fore.GREEN)


async def publish_message_if_autobahn(
    topic: str, message: bytes, print_error: bool = True
):
    if autobahn_instance:
        await autobahn_instance.publish(topic, message)
    elif print_error:
        error("Error: Autobahn instance not initialized publish_message_if_autobahn")


async def stats(message: bytes):
    await publish_message_if_autobahn(STATS_PUBLISH_TOPIC + SUFFIX_STATS, message)


async def log_to_akit(
    topic: str,
    message: list[bool] | list[int] | list[float] | list[str],
):
    instance = StateLogging()
    instance.name = SYSTEM_NAME or "unknown-pi"
    instance.topic = topic
    instance.entries.add(type=from_pytype_to_proto(message), values=message)

    await publish_message_if_autobahn(
        STATS_PUBLISH_TOPIC + SUFFIX_AKIT, instance.SerializeToString()
    )


def from_pytype_to_proto(
    message: list[bool] | list[int] | list[float] | list[str],
) -> DataType:
    if isinstance(message, list) and all(isinstance(item, bool) for item in message):
        return DataType.BOOL
    elif isinstance(message, list) and all(isinstance(item, int) for item in message):
        return DataType.INT
    elif isinstance(message, list) and all(isinstance(item, float) for item in message):
        return DataType.FLOAT
    elif isinstance(message, list) and all(isinstance(item, str) for item in message):
        return DataType.STRING
    else:
        raise ValueError(f"Unsupported type: {type(message)}")


def log(prefix: str, message: str, color: str):
    if autobahn_instance:
        log_message = LogMessage(
            type=StatusType.LOG_MESSAGE,
            prefix=prefix,
            message=message,
            color=color,
            pi_name=SYSTEM_NAME,
        ).SerializeToString()

        try:
            asyncio.create_task(
                autobahn_instance.publish(STATS_PUBLISH_TOPIC, log_message)
            )
        except RuntimeError:
            if main_event_loop:
                main_event_loop.run_coroutine(
                    autobahn_instance.publish(STATS_PUBLISH_TOPIC, log_message),
                )

    print(f"[{prefix}] {color}{message}{colorama.Fore.RESET}")
