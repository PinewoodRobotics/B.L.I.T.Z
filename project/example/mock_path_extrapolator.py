import asyncio
import random
import time
import numpy as np
from project.autobahn.autobahn_python.Listener import Autobahn
from project.example.util.render.position_renderer import PositionVisualizer
from generated.AprilTag_pb2 import AprilTags, Tag
from generated.Imu_pb2 import Imu
from generated.Odometry_pb2 import Odometry
from generated.RobotPosition_pb2 import RobotPosition


class FakeDataGenerator:
    def __init__(
        self,
        randomization_april_tags: float = 0.1,
        randomization_odom: float = 0.2,
        randomization_imu: float = 0.7,
        imu_drift_per_tick: float = 0.01,
        strategy: str = "triangle",
    ):
        self.randomization_april_tags = randomization_april_tags
        self.randomization_odom = randomization_odom
        self.randomization_imu = randomization_imu
        self.strategy = strategy
        self.imu_drift_per_tick = imu_drift_per_tick
        self.last_imu_update = time.time()
        self.imu_drift = (0.0, 0.0, 0.0)

        self.real_position_state: tuple[float, float, float, float, float] = (
            0,
            0,
            0,
            0,
            0,
        )
        self.last_t = 0

    def next_tag(self) -> tuple[float, float, float]:
        x, y, _, _, theta = self.real_position_state
        noisy_x, noisy_y, noisy_theta = self._add_noise(
            [x, y, theta], self.randomization_april_tags
        )

        return (noisy_x, noisy_y, noisy_theta)

    def next_imu(self) -> tuple[float, float, float]:
        current_time = time.time()
        dt = current_time - self.last_imu_update
        self.last_imu_update = current_time

        x, y, _, _, theta = self.real_position_state
        noisy_x, noisy_y, noisy_theta = self._add_noise(
            [x, y, theta], self.randomization_imu
        )

        drift_amount = self.imu_drift_per_tick * dt
        self.imu_drift = (
            self.imu_drift[0] + drift_amount,
            self.imu_drift[1] + drift_amount,
            self.imu_drift[2] + drift_amount,
        )

        return (
            noisy_x + self.imu_drift[0],
            noisy_y + self.imu_drift[1],
            noisy_theta + self.imu_drift[2],
        )

    def get_real_pos(self) -> tuple[float, float, float, float, float]:
        return self.real_position_state

    def next_odom(self) -> tuple[float, float, float, float, float]:
        x, y, vx, vy, theta = self.real_position_state
        noisy_data = self._add_noise([x, y, vx, vy, theta], self.randomization_odom)
        return (
            noisy_data[0],
            noisy_data[1],
            noisy_data[2],
            noisy_data[3],
            noisy_data[4],
        )

    def tick(self, t: float):
        match self.strategy:
            case "triangle":
                self.real_position_state = self._calculate_real_state(
                    self._triangle_strategy(t)
                )
            case "circle":
                self.real_position_state = self._calculate_real_state(
                    self._circle_strategy(t)
                )
            case _:
                raise ValueError(f"Invalid strategy: {self.strategy}")

    def _calculate_real_state(
        self, new_state: tuple[float, float, float]
    ) -> tuple[float, float, float, float, float]:
        dt = self.last_t - time.time()
        if dt == 0:
            return (*new_state[:2], 0, 0, new_state[2])

        vx = (new_state[0] - self.real_position_state[0]) / dt
        vy = (new_state[1] - self.real_position_state[1]) / dt

        return (new_state[0], new_state[1], vx, vy, new_state[2])

    def _add_noise(self, position: list[float], amt_noise: float) -> list[float]:
        return [p + random.uniform(-amt_noise, amt_noise) for p in position]

    def _triangle_strategy(self, t: float) -> tuple[float, float, float]:
        center_x, center_y = 0.0, 0.0
        triangle_size = 2

        p1 = (center_x, center_y + triangle_size, 1.0)
        p2 = (
            center_x - triangle_size * np.sqrt(3) / 2,
            center_y - triangle_size / 2,
            1.0,
        )
        p3 = (
            center_x + triangle_size * np.sqrt(3) / 2,
            center_y - triangle_size / 2,
            1.0,
        )

        t_normalized = t % 1.0
        side = int(t_normalized * 3)
        alpha = (t_normalized * 3) % 1.0

        edges = [(p1, p2), (p2, p3), (p3, p1)]
        p_start, p_end = edges[side]

        # Calculate current position
        x = p_start[0] * (1 - alpha) + p_end[0] * alpha
        y = p_start[1] * (1 - alpha) + p_end[1] * alpha

        # Calculate angle based on direction of movement
        dx = p_end[0] - p_start[0]
        dy = p_end[1] - p_start[1]
        theta = np.degrees(np.arctan2(dy, dx))

        return (x, y, theta)

    def _circle_strategy(self, t: float) -> tuple[float, float, float]:
        center_x, center_y = 0.0, 0.0
        radius = 3
        theta = t * 2 * np.pi
        # Calculate facing direction as tangent to circle
        facing_angle = np.degrees(
            theta + np.pi / 2
        )  # Add 90 degrees to point tangent to circle
        return (
            center_x + radius * np.cos(theta),
            center_y + radius * np.sin(theta),
            facing_angle,
        )


async def main():
    autobahn_server = Autobahn("localhost", 8080)
    await autobahn_server.begin()
    fake_data_generator = FakeDataGenerator(
        randomization_april_tags=0.1,
        randomization_odom=0.2,
        randomization_imu=0.3,
        imu_drift_per_tick=0.07,
        strategy="circle",
    )

    visualizer = PositionVisualizer()
    running = True

    # Callback for receiving position updates
    async def on_position_update(message: bytes):
        nonlocal running
        robot_pos = RobotPosition()
        robot_pos.ParseFromString(message)
        running = visualizer.update_pos(
            "robot",
            (
                robot_pos.estimated_position.position.x,
                robot_pos.estimated_position.position.y,
                np.degrees(
                    np.arctan2(
                        robot_pos.estimated_position.direction.y,
                        robot_pos.estimated_position.direction.x,
                    )
                ),
            ),
        )

    await autobahn_server.subscribe(
        "pos-extrapolator/robot-position",
        on_position_update,
    )

    # Mock AprilTag data generation and publishing
    t = 0
    while running:
        t += 0.05
        fake_data_generator.tick(t)
        tags = AprilTags()
        tags.camera_name = "left"
        tags.timestamp = int(time.time() * 1000)

        tag = Tag()
        (
            tag.position_x_relative,
            tag.position_y_relative,
            tag.angle_relative_to_camera_yaw,
        ) = fake_data_generator.next_tag()
        tags.tags.append(tag)

        odometry = Odometry()
        (
            odometry.position.position.x,
            odometry.position.position.y,
            odometry.velocity.x,
            odometry.velocity.y,
            odometry.position.direction.x,  # TODO: fix
        ) = fake_data_generator.next_odom()

        visualizer.update_pos(
            "odometer",
            (
                odometry.position.position.x,
                odometry.position.position.y,
                np.degrees(
                    np.arctan2(
                        odometry.position.direction.y,
                        odometry.position.direction.x,
                    )
                ),
            ),
        )

        visualizer.update_pos(
            "april_tag",
            (
                tag.position_x_relative,
                tag.position_y_relative,
                tag.angle_relative_to_camera_yaw,
            ),
        )

        imu = Imu()
        (
            imu.position.position.x,
            imu.position.position.y,
            imu.position.direction.x,  # TODO: fix
        ) = fake_data_generator.next_imu()
        imu.acceleration.x = 1.0
        imu.acceleration.y = 1.0

        visualizer.update_pos(
            "imu",
            (
                imu.position.position.x,
                imu.position.position.y,
                np.degrees(
                    np.arctan2(
                        imu.position.direction.y,
                        imu.position.direction.x,
                    )
                ),
            ),
        )

        real_pos = fake_data_generator.get_real_pos()

        visualizer.update_pos(
            "real",
            (
                real_pos[0],
                real_pos[1],
                real_pos[4],
            ),
        )

        await autobahn_server.publish(
            "apriltag/tag",
            tags.SerializeToString(),
        )

        await autobahn_server.publish(
            "odometry/odometry",
            odometry.SerializeToString(),
        )

        await asyncio.sleep(0.1)

    visualizer.close()


if __name__ == "__main__":
    asyncio.run(main())
