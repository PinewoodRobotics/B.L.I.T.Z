import asyncio
import colorama
from enum import Enum

from autobahn_client.client import Autobahn
from blitz.common.util.system import get_system_name
from blitz.generated.proto.python.status.PiStatus_pb2 import LogMessage, StatusType


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


PREFIX = ""
LOG_LEVEL = LogLevel.DEBUG
autobahn_instance: Autobahn | None = None
STATS_PUBLISH_TOPIC = ""


def init_logging(
    prefix: str,
    log_level: LogLevel,
    system_pub_topic: str | None = None,
    autobahn: Autobahn | None = None,
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

    autobahn_instance = autobahn
    colorama.init()
    PREFIX = prefix
    LOG_LEVEL = log_level

    if autobahn_instance:
        if system_pub_topic:
            STATS_PUBLISH_TOPIC = system_pub_topic
        else:
            raise ValueError("System pub topic is required if autobahn is provided")


def set_log_level(log_level: LogLevel):
    global LOG_LEVEL
    LOG_LEVEL = log_level


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


async def stats(message: bytes):
    if autobahn_instance:
        await autobahn_instance.publish(
            STATS_PUBLISH_TOPIC,
            message,
        )


def log(prefix: str, message: str, color: str):
    if autobahn_instance:
        asyncio.create_task(
            autobahn_instance.publish(
                STATS_PUBLISH_TOPIC,
                LogMessage(
                    type=StatusType.LOG_MESSAGE,
                    prefix=prefix,
                    message=message,
                    color=color,
                ).SerializeToString(),
            )
        )

    print(f"[{prefix}] {color}{message}{colorama.Fore.RESET}")
