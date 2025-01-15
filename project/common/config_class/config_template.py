from project.common.error.missing_key_error import MissingKeyError


class ConfigTemplate:
    def check_config(self, config: dict, required_keys: list[str], config_name: str):
        """
        Check if a configuration dictionary contains all required keys.

        Args:
            config (dict): The configuration dictionary to check
            required_keys (list[str]): List of keys that must be present in the config
            config_name (str): Name of the configuration being checked, used in error messages

        Raises:
            MissingKeyError: If any required key is missing from the config dictionary

        Example:
            >>> config = {"key1": "value1", "key2": "value2"}
            >>> required_keys = ["key1", "key3"]
            >>> check_config(config, required_keys, "My Config")
            MissingKeyError: Missing key: 'key3' in My Config
        """

        for key in required_keys:
            if key not in config:
                raise MissingKeyError(key, config_name)
