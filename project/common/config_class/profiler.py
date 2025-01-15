from project.common.config import check_config


required_keys = [
    "activated",
    "profile-function",
    "time-function",
    "output-file",
]


class ProfilerConfig:
    def __init__(self, config: dict):
        check_config(config, required_keys, "ProfilerConfig")
        self.activated: bool = config["activated"]
        self.profile_function: bool = config["profile-function"]
        self.time_function: bool = config["time-function"]
        self.output_file: str = config["output-file"]
