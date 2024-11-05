from std.config_util import check_config


required_keys = ["port"]


class AutobahnConfig:
    def __init__(self, config: dict):
        check_config(config, required_keys, "AutobahnConfig")
        self.port = config["port"]
