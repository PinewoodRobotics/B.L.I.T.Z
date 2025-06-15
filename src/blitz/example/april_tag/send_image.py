import asyncio
import time

import cv2

from blitz.generated.proto.python.Image_pb2 import ImageMessage
from blitz.common.autobahn_python.autobahn import Autobahn
from blitz.common.autobahn_python.util import Address


async def main():
    autobahn = Autobahn(Address("localhost", 8080))
    await autobahn.begin()
    image = cv2.imread("sample_image.png")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    while True:
        await asyncio.sleep(0.5)
        time_current = time.time()
        await autobahn.publish(
            "image_test",
            ImageMessage(
                image=image.tobytes(),
                camera_name="test",
                is_gray=False,
                timestamp=1,
                height=image.shape[0],
                width=image.shape[1],
                image_id=1,
            ).SerializeToString(),
        )
        print(f"Published to image_test in {(time.time() - time_current) * 1000} ms")


if __name__ == "__main__":
    asyncio.run(main())
