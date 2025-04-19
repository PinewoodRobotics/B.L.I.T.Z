import os


def add_cur_dir(path: str):
    return os.path.join(os.path.dirname(__file__), path)
