from project.common import logger


class MissingKeyError(Exception):
    """
    Exception raised when a required configuration key is missing.

    This exception is raised when checking configuration dictionaries
    and a required key is not found. It includes the missing key name
    and the configuration context where it was missing.
    """

    def __init__(self, key: str, config_missing_name: str):
        self.message = f"Missing key: '{key}' in {config_missing_name}"
        logger.error(self.message)
        super().__init__(self.message)

    def __str__(self):
        return self.message
