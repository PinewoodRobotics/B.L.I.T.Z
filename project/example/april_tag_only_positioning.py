import asyncio
import cv2
import numpy as np
from project.autobahn.autobahn_python.autobahn import Autobahn
from project.example.util.render.position_renderer import PositionVisualizer
from generated.Image_pb2 import ImageMessage
from generated.RobotPosition_pb2 import RobotPosition


async def main():
    autobahn_server = Autobahn("localhost", 8080)
    await autobahn_server.begin()
    stop_event = asyncio.Event()

    position_renderer = PositionVisualizer(max_min_x=[-10, 10], max_min_y=[-10, 10])

    async def on_position_update(message: bytes):
        robot_pos = RobotPosition()
        robot_pos.ParseFromString(message)
        position_renderer.update_poses(
            {
                "robot": (
                    robot_pos.estimated_position.position.x,
                    robot_pos.estimated_position.position.y,
                    np.arctan2(
                        robot_pos.estimated_position.direction.y,
                        robot_pos.estimated_position.direction.x,
                    ),
                ),
            }
        )

    async def on_camera_update(message: bytes):
        img = ImageMessage()
        img.ParseFromString(message)

        # Convert bytes to numpy array
        nparr = np.frombuffer(img.image, np.uint8)

        # Check if the image is grayscale or color
        if img.is_gray:
            frame = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            frame = cv2.cvtColor(
                frame, cv2.COLOR_GRAY2BGR
            )  # Convert to BGR for consistent display
        else:
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Display the frame
        cv2.imshow("Camera Feed", frame)
        cv2.waitKey(1)  # Wait 1ms to update the window

    await autobahn_server.subscribe(
        "pos-extrapolator/robot-position", on_position_update
    )

    await autobahn_server.subscribe("apriltag/camera", on_camera_update)

    # Add cleanup for OpenCV windows
    try:
        await stop_event.wait()
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    asyncio.run(main())
