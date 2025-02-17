import colorama
from enum import Enum

from pyinstrument import Profiler


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


PREFIX = ""
LOG_LEVEL = LogLevel.DEBUG


def init_logging(prefix: str, log_level: LogLevel):
    """
    Initialize the logging system with a prefix and log level.

    Args:
        prefix (str): The prefix to prepend to all log messages
        log_level (LogLevel): The minimum log level to display messages for
    """
    global PREFIX
    global LOG_LEVEL
    colorama.init()

    PREFIX = prefix
    LOG_LEVEL = log_level


def set_log_level(log_level: LogLevel):
    global LOG_LEVEL
    LOG_LEVEL = log_level


def message(message: str):
    if LOG_LEVEL == LogLevel.DEBUG:
        log(PREFIX, message, colorama.Fore.RESET)


def error(message: str):
    if LOG_LEVEL == LogLevel.DEBUG:
        log(PREFIX, message, colorama.Fore.RED)


def warning(message: str):
    if LOG_LEVEL == LogLevel.DEBUG:
        log(PREFIX, message, colorama.Fore.YELLOW)


def info(message: str):
    if LOG_LEVEL == LogLevel.DEBUG:
        log(PREFIX, message, colorama.Fore.CYAN)


def debug(message: str):
    if LOG_LEVEL == LogLevel.DEBUG:
        log(PREFIX, message, colorama.Fore.BLUE)


def success(message: str):
    if LOG_LEVEL == LogLevel.DEBUG:
        log(PREFIX, message, colorama.Fore.GREEN)


def log_profiler(profiler: Profiler):
    if LOG_LEVEL == LogLevel.DEBUG:
        print(profiler.output_text(unicode=True, color=True))


def log(prefix: str, message: str, color: str):
    print(f"[{prefix}] {color}{message}{colorama.Fore.RESET}")
