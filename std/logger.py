import colorama
from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


PREFIX = ""
LOG_LEVEL = LogLevel.DEBUG


def init_logging(prefix: str, log_level: LogLevel):
    global PREFIX
    global LOG_LEVEL
    colorama.init()

    PREFIX = prefix
    LOG_LEVEL = log_level


def message(message: str):
    if LOG_LEVEL == LogLevel.DEBUG:
        log(PREFIX, message, colorama.Fore.RESET)


def error(message: str):
    if LOG_LEVEL == LogLevel.ERROR:
        log(PREFIX, message, colorama.Fore.RED)


def warning(message: str):
    if LOG_LEVEL == LogLevel.WARNING:
        log(PREFIX, message, colorama.Fore.YELLOW)


def info(message: str):
    if LOG_LEVEL == LogLevel.INFO:
        log(PREFIX, message, colorama.Fore.CYAN)


def debug(message: str):
    if LOG_LEVEL == LogLevel.DEBUG:
        log(PREFIX, message, colorama.Fore.BLUE)


def success(message: str):
    if LOG_LEVEL == LogLevel.DEBUG:
        log(PREFIX, message, colorama.Fore.GREEN)


def log(prefix: str, message: str, color: str):
    print(f"[{prefix}] {color}{message}{colorama.Fore.RESET}")
