import asyncio
import json
import time
import cv2
import nats

from config import NATS_PORT


async def main():
    nc = await nats.connect(f"nats://localhost:{NATS_PORT}")

    async def april_tag_recognition_cb(msg):
        print(msg)

    await nc.subscribe("april_tag_recognition", cb=april_tag_recognition_cb)


if __name__ == "__main__":
    asyncio.run(main())
