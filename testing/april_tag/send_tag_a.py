import asyncio
import math

import numpy as np

from blitz.generated.proto.python.AprilTag_pb2 import AprilTags, Tag
from blitz.common.autobahn_python.autobahn import Autobahn
from blitz.common.autobahn_python.util import Address


async def main():
    autobahn = Autobahn(Address("localhost", 8080))
    await autobahn.begin()
    angle = 0
    radius = 3
    while True:
        await asyncio.sleep(0.02)
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        z = 2 + math.sin(angle)

        angle += 0.1

        await autobahn.publish(
            "april_tag",
            AprilTags(
                camera_name="test",
                image_id=1,
                timestamp=1,
                tags=[
                    Tag(
                        tag_id=1,
                        position_x_relative=x,
                        position_y_relative=y,
                        position_z_relative=z,
                        pose_R=np.array([1, 0, 0, 0, 1, 0, 0, 0, 1]).tolist(),
                        pose_t=(x, y, z),
                        tag_size=1,
                        distance_to_camera=0,
                        angle_relative_to_camera_yaw=0,
                        angle_relative_to_camera_pitch=0,
                        pose_err=0,
                    )
                ],
            ).SerializeToString(),
        )


if __name__ == "__main__":
    asyncio.run(main())
