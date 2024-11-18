import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train YOLOv8 with custom parameters.")

    parser.add_argument(
        "--train",
        type=str,
        default="false",
        help="If you want to train or not. Default is false.",
    )

    return parser.parse_args()
