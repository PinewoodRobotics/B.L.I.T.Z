import asyncio
import cv2
import numpy as np
from generated.util.position_pb2 import Position2d
from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address
from project.example.util.render.position_render_game import PositionVisualizerGame
from generated.Image_pb2 import ImageMessage
from generated.RobotPosition_pb2 import RobotPosition


async def main():
    autobahn_server = Autobahn(Address("10.47.65.7", 8080))
    await autobahn_server.begin()
    stop_event = asyncio.Event()

    # Store target position, direction, and waiting state
    target_position = [0, 0]
    target_direction = [1, 0]  # Default direction vector
    waiting_for_direction = [False]

    async def async_on_click(x: float, y: float):
        nonlocal target_position, target_direction

        if not waiting_for_direction[0]:
            # First click - set position
            target_position[0] = x
            target_position[1] = y
            waiting_for_direction[0] = True
            print(f"Set target position: ({x}, {y}). Click again to set direction.")
        else:
            # Second click - calculate direction vector
            dx = x - target_position[0]
            dy = y - target_position[1]
            # Normalize the direction vector
            magnitude = np.sqrt(dx * dx + dy * dy)
            if magnitude > 0:  # Avoid division by zero
                dx /= magnitude
                dy /= magnitude
                target_direction[0] = dx
                target_direction[1] = dy

            # Create and send message with position and direction
            pos_msg = Position2d()
            pos_msg.position.x = target_position[0]
            pos_msg.position.y = target_position[1]
            # Calculate angle and use trig functions for direction
            angle = np.arctan2(dy, dx)
            pos_msg.direction.x = np.cos(angle)  # sin component
            pos_msg.direction.y = np.sin(angle)  # cos component
            await autobahn_server.publish("auto/command", pos_msg.SerializeToString())
            waiting_for_direction[0] = False
            print(f"Set direction: (sin={np.sin(angle):.2f}, cos={np.cos(angle):.2f})")

    def on_click(x: float, y: float):
        asyncio.create_task(async_on_click(x, y))

    position_renderer = PositionVisualizerGame(
        max_min_x=[-5, 5],
        max_min_y=[-5, 5],
        click_callback=on_click,
        window_size=(1200, 950),
    )

    async def on_position_update(message: bytes):
        robot_pos = RobotPosition()
        robot_pos.ParseFromString(message)
        position_renderer.update_poses(
            {
                "robot": (
                    robot_pos.estimated_position.position.x,
                    robot_pos.estimated_position.position.y,
                    np.degrees(
                        np.arctan2(
                            -robot_pos.estimated_position.direction.y,
                            robot_pos.estimated_position.direction.x,
                        )
                    ),
                ),
                "target": (
                    target_position[0],
                    target_position[1],
                    np.degrees(np.arctan2(target_direction[1], target_direction[0])),
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
