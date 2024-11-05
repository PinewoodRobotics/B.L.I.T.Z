import toml


class Config:
    def __init__(self, config_path: str):
        self.config = toml.load(config_path)
