import json


def get_config_data(file_path: str):
    with open(file_path, "r") as file:
        return json.load(file)


def write_config_data(data):
    with open("file_path", "w") as file:
        file.write(json.dumps(data))
