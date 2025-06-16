import colorama
from enum import Enum

from blitz.common.autobahn_python.autobahn import Autobahn
from blitz.common.util.system import get_system_name
from blitz.generated.proto.python.status.PiStatus_pb2 import LogMessage


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
AUTOBAHN_LOG_LEVEL = LOG_LEVEL
autobahn_instance: Autobahn | None = None
STATS_PUBLISH_TOPIC = ""


def init_logging(
    prefix: str,
    log_level: LogLevel,
    autobahn: Autobahn | None = None,
    autobahn_log_level: LogLevel | None = None,
):
    """
    Initialize the logging system with a prefix and log level.

    Args:
        prefix (str): The prefix to prepend to all log messages
        log_level (LogLevel): The minimum log level to display messages for
    """
    global PREFIX
    global LOG_LEVEL
    global AUTOBAHN_LOG_LEVEL
    global STATS_PUBLISH_TOPIC
    global autobahn_instance

    autobahn_instance = autobahn
    colorama.init()
    PREFIX = prefix
    LOG_LEVEL = log_level
    AUTOBAHN_LOG_LEVEL = log_level
    if autobahn_log_level:
        AUTOBAHN_LOG_LEVEL = autobahn_log_level

    STATS_PUBLISH_TOPIC = get_system_name() + "/watchdog/stats"


async def set_log_level(log_level: LogLevel):
    global LOG_LEVEL
    LOG_LEVEL = log_level


async def message(message: str):
    if LOG_LEVEL <= LogLevel.INFO:
        await log(PREFIX, message, colorama.Fore.RESET, LogLevel.INFO.get_importance())


async def error(message: str):
    if LOG_LEVEL <= LogLevel.ERROR:
        await log(PREFIX, message, colorama.Fore.RED, LogLevel.ERROR.get_importance())


async def warning(message: str):
    if LOG_LEVEL <= LogLevel.WARNING:
        await log(
            PREFIX, message, colorama.Fore.YELLOW, LogLevel.WARNING.get_importance()
        )


async def info(message: str):
    if LOG_LEVEL <= LogLevel.INFO:
        await log(PREFIX, message, colorama.Fore.CYAN, LogLevel.INFO.get_importance())


async def debug(message: str):
    if LOG_LEVEL <= LogLevel.DEBUG:
        await log(PREFIX, message, colorama.Fore.BLUE, LogLevel.DEBUG.get_importance())


async def success(message: str):
    if LOG_LEVEL <= LogLevel.INFO:
        await log(PREFIX, message, colorama.Fore.GREEN, LogLevel.INFO.get_importance())


async def stats(message: bytes):
    if autobahn_instance:
        await autobahn_instance.publish(
            STATS_PUBLISH_TOPIC,
            message,
        )


async def log(prefix: str, message: str, color: str, autobahn_level: int):
    if autobahn_instance and autobahn_level <= AUTOBAHN_LOG_LEVEL.get_importance():
        await autobahn_instance.publish(
            STATS_PUBLISH_TOPIC,
            LogMessage(prefix=prefix, message=message, color=color).SerializeToString(),
        )

    print(f"[{prefix}] {color}{message}{colorama.Fore.RESET}")
