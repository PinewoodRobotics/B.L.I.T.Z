import asyncio
import random
import time
import pygame
import numpy as np
from project.autobahn.autobahn_python.autobahn import Autobahn
from project.common.config import Config, Module
from project.generated.project.common.proto.AprilTag_pb2 import AprilTags
from project.generated.project.common.proto.RobotPosition_pb2 import RobotPosition


class PositionVisualizer:
    def __init__(self, window_size=(800, 600), scale=100, trail_length=50):
        pygame.init()
        self.window_size = window_size
        self.scale = scale  # pixels per meter
        self.screen = pygame.display.set_mode(window_size)
        pygame.display.set_caption("Robot Position Visualizer")
        self.background_color = (255, 255, 255)
        self.robot_color = (255, 0, 0)  # Estimated position in red
        self.real_color = (0, 255, 0)  # Real position in green
        self.robot_size = 10

        # Trail parameters
        self.trail_length = trail_length
        self.robot_trail = []  # [(x, y, angle), ...]
        self.real_trail = []

        # Store current positions
        self.robot_pos = None
        self.real_pos = None

    def update_robot_pos(self, position: RobotPosition):
        """Update estimated robot position and trail"""
        self.robot_pos = (
            position.estimated_position[0],
            position.estimated_position[1],
            position.estimated_rotation[1],
        )
        self.robot_trail.append(self.robot_pos)
        if len(self.robot_trail) > self.trail_length:
            self.robot_trail.pop(0)

        self._draw_frame()
        return True

    def update_real_pos(self, position: tuple[float, float, float]):
        """Update real position from AprilTags and trail"""
        self.real_pos = position

        self.real_trail.append(self.real_pos)
        if len(self.real_trail) > self.trail_length:
            self.real_trail.pop(0)

        self._draw_frame()

    def _draw_frame(self):
        """Internal method to handle all drawing operations"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False

        self.screen.fill(self.background_color)

        # Draw trails
        self._draw_trail(self.real_trail, self.real_color)
        self._draw_trail(self.robot_trail, self.robot_color)

        # Draw current positions
        if self.real_pos:
            self._draw_position(self.real_pos, self.real_color)
        if self.robot_pos:
            self._draw_position(self.robot_pos, self.robot_color)

        pygame.display.flip()
        return True

    def _draw_trail(self, trail, base_color):
        """Draw position trail with fading effect"""
        for i, pos in enumerate(trail):
            # Calculate alpha based on position in trail
            alpha = int(255 * (i + 1) / len(trail))
            color = (*base_color[:3], alpha)

            # Convert to screen coordinates
            screen_x = self.window_size[0] // 2 + pos[0] * self.scale
            screen_y = self.window_size[1] // 2 - pos[1] * self.scale

            # Create a surface for the trail point
            trail_surface = pygame.Surface(
                (self.robot_size * 2, self.robot_size * 2), pygame.SRCALPHA
            )
            pygame.draw.circle(
                trail_surface,
                color,
                (self.robot_size, self.robot_size),
                self.robot_size // 2,
            )
            self.screen.blit(
                trail_surface, (screen_x - self.robot_size, screen_y - self.robot_size)
            )

    def _draw_position(self, pos, color):
        """Draw current position and direction indicator"""
        screen_x = self.window_size[0] // 2 + pos[0] * self.scale
        screen_y = self.window_size[1] // 2 - pos[1] * self.scale

        # Draw position
        pygame.draw.circle(
            self.screen,
            color,
            (int(screen_x), int(screen_y)),
            self.robot_size,
        )

        # Draw direction indicator
        angle = np.deg2rad(pos[2])
        end_x = screen_x + 20 * np.cos(angle)
        end_y = screen_y - 20 * np.sin(angle)
        pygame.draw.line(
            self.screen,
            color,
            (screen_x, screen_y),
            (end_x, end_y),
            2,
        )


async def main():
    autobahn_server = Autobahn("localhost", 8080)
    await autobahn_server.begin()

    visualizer = PositionVisualizer()
    running = True

    # Callback for receiving position updates
    async def on_position_update(message: bytes):
        nonlocal running
        robot_pos = RobotPosition()
        robot_pos.ParseFromString(message)
        running = visualizer.update_robot_pos(robot_pos)

    await autobahn_server.subscribe(
        "pos-extrapolator/robot-position",
        on_position_update,
    )

    # Mock AprilTag data generation and publishing
    while running:
        # Create mock AprilTag data
        tags = AprilTags()
        tags.camera_name = "left"

        t = time.time()
        pos_x_relative, pos_y_relative, pos_z_relative = (
            2 * np.cos(t * 0.5),
            2 * np.sin(t * 0.5),
            1.0,
        )

        tag = tags.tags.add()
        tag.position_x_relative = pos_x_relative + random.random() * 0.7
        tag.position_y_relative = pos_y_relative + random.random() * 0.7
        tag.position_z_relative = pos_z_relative + random.random()
        tag.angle_relative_to_camera_pitch = 0
        tag.angle_relative_to_camera_yaw = np.rad2deg(t * 0.5)  # Rotate with motion

        visualizer.update_real_pos(
            (
                tag.position_x_relative,
                tag.position_y_relative,
                tag.angle_relative_to_camera_yaw,
            )
        )

        # Publish mock data
        await autobahn_server.publish(
            "apriltag/tag",
            tags.SerializeToString(),
        )

        await asyncio.sleep(0.1)  # 10 Hz update rate

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
