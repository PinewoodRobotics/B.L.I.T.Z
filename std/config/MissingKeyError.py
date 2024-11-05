from std import logger


class MissingKeyError(Exception):
    def __init__(self, key: str, config_missing_name: str):
        self.message = f"Missing key: '{key}' in {config_missing_name}"
        logger.error(self.message)
        super().__init__(self.message)

    def __str__(self):
        return self.message
