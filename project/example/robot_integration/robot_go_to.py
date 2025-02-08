import asyncio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Arrow
from matplotlib.backend_bases import MouseEvent
from generated.util.position_pb2 import Position2d
from generated.util.vector_pb2 import Vector2
from project.autobahn.autobahn_python.autobahn import Autobahn
from generated.RobotPosition_pb2 import RobotPosition

POST_COMMAND = "navigation/set_goal"


class RobotNavigator:
    def __init__(self, max_min_x=[-10, 10], max_min_y=[-10, 10]):
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlim(max_min_x)
        self.ax.set_ylim(max_min_y)
        self.ax.grid(True)
        self.robot_position = None
        self.robot_scatter = None
        self.arrow_length = 0.5
        self.target_line = None

        # Connect click event
        self.fig.canvas.mpl_connect("button_press_event", self.on_click)  # type: ignore

        # Initialize Autobahn
        self.autobahn = None

    async def initialize_autobahn(self):
        self.autobahn = Autobahn("localhost", 8080)
        await self.autobahn.begin()
        await self.autobahn.subscribe(
            "pos-extrapolator/robot-position", self.on_position_update
        )

    async def on_position_update(self, message: bytes):
        robot_pos = RobotPosition()
        robot_pos.ParseFromString(message)

        x = robot_pos.estimated_position.position.x
        y = robot_pos.estimated_position.position.y
        self.robot_position = (x, y)
        theta = np.arctan2(
            robot_pos.estimated_position.direction.y,
            robot_pos.estimated_position.direction.x,
        )

        if self.robot_scatter is None:
            self.robot_scatter = self.ax.scatter([x], [y], color="blue", s=100)
        else:
            self.robot_scatter.set_offsets([[x, y]])

        for artist in self.ax.artists:
            if isinstance(artist, Arrow):
                artist.remove()

        arrow = Arrow(
            x,
            y,
            self.arrow_length * np.cos(theta),
            self.arrow_length * np.sin(theta),
            width=0.3,
            color="red",
        )
        self.ax.add_artist(arrow)

        # Update target line if it exists
        if self.target_line is not None:
            self.target_line.set_xdata([x, self.target_line.get_xdata()[1]])
            self.target_line.set_ydata([y, self.target_line.get_ydata()[1]])

        plt.draw()
        self.fig.canvas.flush_events()

    def on_click(self, event: MouseEvent):
        if event.inaxes != self.ax:
            return

        x, y = event.xdata, event.ydata
        print(f"Clicked at position: ({x:.2f}, {y:.2f})")

        # Remove existing target line if it exists
        if self.target_line is not None:
            self.target_line.remove()

        # Draw new target line if we have a robot position
        if self.robot_position is not None and x is not None and y is not None:
            self.target_line = self.ax.plot(
                [float(self.robot_position[0]), float(x)],
                [float(self.robot_position[1]), float(y)],
                "g-",
                linewidth=2,
            )[0]

        asyncio.create_task(self.send_navigation_command(x, y))  # type: ignore

    async def send_navigation_command(self, x: float, y: float):
        if self.autobahn is None:
            print("Autobahn not initialized")
            return

        nav_command = Position2d(position=Vector2(x, y), direction=Vector2(0, 0))
        await self.autobahn.publish(POST_COMMAND, nav_command.SerializeToString())


async def main():
    navigator = RobotNavigator()
    await navigator.initialize_autobahn()

    plt.ion()
    plt.show()

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    finally:
        plt.close("all")


if __name__ == "__main__":
    asyncio.run(main())
