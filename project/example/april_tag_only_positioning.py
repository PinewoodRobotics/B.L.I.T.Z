import asyncio
from project.autobahn.autobahn_python.autobahn import Autobahn
from project.example.util.render.position_renderer import PositionVisualizer
from project.generated.project.common.proto.RobotPosition_pb2 import RobotPosition


async def main():
    autobahn_server = Autobahn("localhost", 8080)
    await autobahn_server.begin()

    position_renderer = PositionVisualizer()

    async def on_position_update(message: bytes):
        robot_pos = RobotPosition()
        robot_pos.ParseFromString(message)
        position_renderer.update_pos(
            "robot",
            (
                robot_pos.estimated_position[0],
                robot_pos.estimated_position[1],
                robot_pos.estimated_rotation[1],
            ),
        )

    await autobahn_server.subscribe(
        "pos-extrapolator/robot-position", on_position_update
    )

    while True:
        position_renderer.update_pos("center", (0, 0, 0))
        await asyncio.sleep(0.01)


if __name__ == "__main__":
    asyncio.run(main())
