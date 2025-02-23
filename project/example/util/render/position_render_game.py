import pygame
from typing import Dict
import time
import math


class PositionVisualizerGame:
    def __init__(
        self,
        window_size=(800, 600),  # Default window size in pixels
        max_min_x=(-20, 20),
        max_min_y=(-20, 20),
        trail_length=25,
    ):
        pygame.init()
        self.screen = pygame.display.set_mode(
            window_size, pygame.HWSURFACE | pygame.DOUBLEBUF
        )
        pygame.display.set_caption("Position Visualizer")

        # Store window parameters
        self.window_size = window_size
        self.max_min_x = max_min_x
        self.max_min_y = max_min_y
        self.scale_x = window_size[0] / (max_min_x[1] - max_min_x[0])
        self.scale_y = window_size[1] / (max_min_y[1] - max_min_y[0])

        # Trail parameters
        self.trail_length = trail_length
        self.positions = {}
        self.colors = [
            (255, 0, 0),  # Red
            (0, 255, 0),  # Green
            (0, 0, 255),  # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (255, 128, 0),  # Orange
            (128, 0, 255),  # Purple
            (0, 255, 128),  # Lime
            (255, 0, 128),  # Pink
        ]
        self.color_idx = 0

        # Performance monitoring
        self.last_render_time = time.time()
        self.min_render_interval = 1 / 60  # Target 60 FPS
        self.clock = pygame.time.Clock()

        # Font for labels
        self.font = pygame.font.Font(None, 24)
        self.axis_font = pygame.font.Font(None, 20)

        # Margin for axes
        self.margin = 40

    def world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        """Convert world coordinates to screen coordinates"""
        screen_x = int(self.margin + (x - self.max_min_x[0]) * self.scale_x)
        # Flip y-axis since pygame's origin is top-left
        screen_y = int(
            self.window_size[1] - self.margin - (y - self.max_min_y[0]) * self.scale_y
        )
        return (screen_x, screen_y)

    def update_pos(self, name: str, position: tuple[float, float, float]):
        """Update position for a named entity"""
        if name not in self.positions:
            self.positions[name] = {
                "trail": [],
                "color": self.colors[self.color_idx % len(self.colors)],
            }
            self.color_idx += 1

        pos_data = self.positions[name]
        pos_data["trail"].append(position)

        if len(pos_data["trail"]) > self.trail_length:
            pos_data["trail"].pop(0)

        current_time = time.time()
        if current_time - self.last_render_time >= self.min_render_interval:
            self._draw_frame()
            self.last_render_time = current_time

    def update_poses(self, poses: Dict[str, tuple[float, float, float]]):
        """Update positions for multiple named entities"""
        for name, position in poses.items():
            self.update_pos(name, position)

    def _draw_frame(self):
        """Update all visualizations"""
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
                return False

        # Clear screen
        self.screen.fill((255, 255, 255))  # White background

        # Draw axes
        axes_color = (0, 0, 0)  # Black
        _origin = self.world_to_screen(0, 0)

        # X-axis
        pygame.draw.line(
            self.screen,
            axes_color,
            (self.margin, self.window_size[1] - self.margin),
            (self.window_size[0] - self.margin, self.window_size[1] - self.margin),
            2,
        )
        # Y-axis
        pygame.draw.line(
            self.screen,
            axes_color,
            (self.margin, self.margin),
            (self.margin, self.window_size[1] - self.margin),
            2,
        )

        # Draw grid and labels
        grid_color = (220, 220, 220)  # Lighter gray
        for x in range(int(self.max_min_x[0]), int(self.max_min_x[1]) + 1):
            start = self.world_to_screen(x, self.max_min_y[0])
            end = self.world_to_screen(x, self.max_min_y[1])
            if x == 0:  # Draw axis in black
                pygame.draw.line(self.screen, axes_color, start, end, 2)
            else:  # Draw grid in light gray
                pygame.draw.line(self.screen, grid_color, start, end, 1)
            # X-axis labels
            label = self.axis_font.render(str(x), True, axes_color)
            label_pos = (
                start[0] - label.get_width() // 2,
                self.window_size[1] - self.margin + 5,
            )
            self.screen.blit(label, label_pos)

        for y in range(int(self.max_min_y[0]), int(self.max_min_y[1]) + 1):
            start = self.world_to_screen(self.max_min_x[0], y)
            end = self.world_to_screen(self.max_min_x[1], y)
            if y == 0:  # Draw axis in black
                pygame.draw.line(self.screen, axes_color, start, end, 2)
            else:  # Draw grid in light gray
                pygame.draw.line(self.screen, grid_color, start, end, 1)
            # Y-axis labels
            label = self.axis_font.render(str(y), True, axes_color)
            label_pos = (
                self.margin - label.get_width() - 5,
                start[1] - label.get_height() // 2,
            )
            self.screen.blit(label, label_pos)

        # Draw trails and positions
        legend_y = 10
        for name, pos_data in self.positions.items():
            trail = pos_data["trail"]
            if not trail:
                continue

            # Draw trail with fade effect
            for i in range(len(trail) - 1):
                _alpha = int(255 * (i + 1) / len(trail))
                color = pos_data["color"]
                start = self.world_to_screen(trail[i][0], trail[i][1])
                end = self.world_to_screen(trail[i + 1][0], trail[i + 1][1])
                # Draw thicker anti-aliased line
                pygame.draw.aalines(self.screen, color, False, [start, end], 1)

            # Draw current position with anti-aliasing
            current_pos = trail[-1]
            screen_pos = self.world_to_screen(current_pos[0], current_pos[1])
            pygame.draw.circle(
                self.screen, pos_data["color"], screen_pos, 6
            )  # Outer circle
            pygame.draw.circle(
                self.screen, (255, 255, 255), screen_pos, 4
            )  # Inner circle
            pygame.draw.circle(
                self.screen, pos_data["color"], screen_pos, 3
            )  # Center dot

            # Draw direction indicator
            angle = math.radians(current_pos[2])
            arrow_length = 20  # pixels
            arrow_end = (
                screen_pos[0] + arrow_length * math.cos(angle),
                screen_pos[1]
                - arrow_length
                * math.sin(angle),  # Negative because pygame y is inverted
            )
            # Draw thicker anti-aliased line for direction
            pygame.draw.aalines(
                self.screen, pos_data["color"], False, [screen_pos, arrow_end], 1
            )

            # Draw legend
            text = self.font.render(name, True, pos_data["color"])
            self.screen.blit(text, (10, legend_y))
            legend_y += 25

        pygame.display.flip()
        self.clock.tick(60)  # Limit to 60 FPS
        return True

    def close(self):
        """Close the visualization window"""
        pygame.quit()
