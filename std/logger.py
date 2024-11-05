import colorama

PREFIX = ""
LOG_LEVEL = "INFO"


def init_logging(prefix: str, log_level: str):
    global PREFIX
    global LOG_LEVEL
    colorama.init()

    PREFIX = prefix
    LOG_LEVEL = log_level


def message(message: str):
    if LOG_LEVEL == "DEBUG":
        log(PREFIX, message, colorama.Fore.RESET)


def error(message: str):
    if LOG_LEVEL == "ERROR":
        log(PREFIX, message, colorama.Fore.RED)


def warning(message: str):
    if LOG_LEVEL == "WARNING":
        log(PREFIX, message, colorama.Fore.YELLOW)


def info(message: str):
    if LOG_LEVEL == "INFO":
        log(PREFIX, message, colorama.Fore.CYAN)


def debug(message: str):
    if LOG_LEVEL == "DEBUG":
        log(PREFIX, message, colorama.Fore.BLUE)


def success(message: str):
    if LOG_LEVEL == "DEBUG":
        log(PREFIX, message, colorama.Fore.GREEN)


def log(prefix: str, message: str, color: str):
    print(f"{prefix} {color}{message}{colorama.Fore.RESET}")
