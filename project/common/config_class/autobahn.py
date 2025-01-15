from project.common.config_class.config_template import ConfigTemplate


required_keys = ["port"]


class AutobahnConfig(ConfigTemplate):
    def __init__(self, config: dict):
        self.check_config(config, required_keys, "AutobahnConfig")
        self.port = config["port"]
