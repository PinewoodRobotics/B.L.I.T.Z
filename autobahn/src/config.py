from colorama import Fore


required = ["self-port", "peers", "internal-sub-port", "internal-pub-port"]


class Config:
    def __init__(self, config: dict):
        for key in required:
            if key not in config:
                log_error(f"Required config {key} not found!")
                exit(1)

        self.peers = config["peers"]
        self.self_port = config["self-port"]
        self.internal_port = config["internal-sub-port"]
        self.internal_sub_port = config["internal-sub-port"]
        self.internal_pub_port = config["internal-pub-port"]


def log_error(message: str):
    print(Fore.RED, f"[Com Config Loader] '{message}'")
