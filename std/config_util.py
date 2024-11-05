from std.error.MissingKeyError import MissingKeyError


def check_config(config: dict, required_keys: list[str], config_name: str):
    for key in required_keys:
        if key not in config:
            raise MissingKeyError(key, config_name)
