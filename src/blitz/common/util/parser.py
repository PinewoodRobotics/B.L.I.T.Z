from argparse import ArgumentParser


def get_default_process_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("--config", type=str, default=None)
    return parser
