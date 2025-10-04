import time
from logging import info

import cv2
import numpy as np

from backend.python.common.debug.logger import stats_for_nerds
from backend.generated.proto.python.sensor.camera_sensor_pb2 import (
    ImageCompression,
    ImageData,
    ImageFormat,
)


def from_proto_format(format: ImageFormat) -> int:
    if format == ImageFormat.RGB:
        return cv2.IMREAD_COLOR_RGB
    elif format == ImageFormat.BGR:
        return cv2.IMREAD_COLOR_BGR
    elif format == ImageFormat.RGBA:
        return cv2.IMREAD_COLOR_RGB
    elif format == ImageFormat.BGRA:
        return cv2.IMREAD_COLOR_RGB
    elif format == ImageFormat.GRAY:
        return cv2.IMREAD_GRAYSCALE
    else:
        raise ValueError(f"Invalid image format: {format}")


def from_proto_format_to_n_channels(format: ImageFormat) -> int:
    if format == ImageFormat.RGB:
        return 3
    elif format == ImageFormat.BGR:
        return 3
    elif format == ImageFormat.RGBA:
        return 4
    elif format == ImageFormat.BGRA:
        return 4
    elif format == ImageFormat.GRAY:
        return 1
    else:
        raise ValueError(f"Invalid image format: {format}")


@stats_for_nerds(print_stats=False)
def compress_image(
    image: np.ndarray,
    compression_quality: int = 90,
) -> np.ndarray:
    _, image = cv2.imencode(
        ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, compression_quality]
    )

    return image


@stats_for_nerds(print_stats=False)
def decode_image(proto_image: ImageData) -> np.ndarray:
    channels = from_proto_format_to_n_channels(proto_image.format)
    if proto_image.compression == ImageCompression.JPEG:
        return cv2.imdecode(
            np.frombuffer(proto_image.image, dtype=np.uint8),
            from_proto_format(proto_image.format),
        )
    else:
        return np.frombuffer(proto_image.image, dtype=np.uint8).reshape(
            (proto_image.height, proto_image.width, channels)
        )


def from_proto_image(bytes: bytes) -> np.ndarray:
    proto_image = ImageData()
    proto_image.ParseFromString(bytes)
    return decode_image(proto_image)


def encode_image(
    image: np.ndarray,
    format: ImageFormat,
    do_compress: bool = True,
    compression_quality: int = 90,
) -> ImageData:
    width = image.shape[1]
    height = image.shape[0]

    if do_compress:
        image = compress_image(image, compression_quality)

    return ImageData(
        image=image.tobytes(),
        width=width,
        height=height,
        compression=ImageCompression.JPEG if do_compress else ImageCompression.NONE,
        format=format,
    )
