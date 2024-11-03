import colorama


def log_error(prefix, message):
    log(prefix, colorama.Fore.RED + message)


def log_info(prefix, message):
    log(prefix, colorama.Fore.BLUE + message)


def log(prefix, message):
    print(f"[Camera Feed Cleaner {prefix}]", message, colorama.Style.RESET_ALL)
