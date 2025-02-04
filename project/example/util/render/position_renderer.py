from typing import Dict
from matplotlib import pyplot as plt
import numpy as np
import time


class PositionVisualizer:
    def __init__(
        self,
        window_size=(10, 8),
        max_min_x=(-20, 20),
        max_min_y=(-20, 20),
        trail_length=25,
    ):
        # Setup matplotlib figure
        plt.ion()  # Enable interactive mode
        self.fig, self.ax = plt.subplots(figsize=window_size)
        self.ax.set_aspect("equal")
        self.ax.grid(True)

        # Trail parameters
        self.trail_length = trail_length
        self.positions = {}  # Change to regular dict
        self.colors = plt.colormaps["rainbow"](np.linspace(0, 1, 10))  # Color cycle
        self.color_idx = 0

        # Setup plot limits
        self.max_min_x = max_min_x
        self.max_min_y = max_min_y
        plt.show()

        self.last_render_time = time.time()
        self.min_render_interval = 1 / 15  # Target 60 FPS max
        self.frame_times = []  # Store last N frame times for averaging
        self.max_frame_times = 15  # Number of frames to average

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

        # Maintain trail length
        if len(pos_data["trail"]) > self.trail_length:
            pos_data["trail"].pop(0)

        # Only render if enough time has passed since last render
        current_time = time.time()
        if current_time - self.last_render_time >= self.min_render_interval:
            self._draw_frame()
            self.last_render_time = current_time

        return True

    def update_poses(self, poses: Dict[str, tuple[float, float, float]]):
        """Update positions for multiple named entities"""
        for name, position in poses.items():
            if name not in self.positions:
                self.positions[name] = {
                    "trail": [],
                    "color": self.colors[self.color_idx % len(self.colors)],
                }
                self.color_idx += 1

            pos_data = self.positions[name]
            pos_data["trail"].append(position)

            # Maintain trail length
            if len(pos_data["trail"]) > self.trail_length:
                pos_data["trail"].pop(0)

        # Only render if enough time has passed since last render
        current_time = time.time()
        if current_time - self.last_render_time >= self.min_render_interval:
            self._draw_frame()
            self.last_render_time = current_time

    def _draw_frame(self):
        """Update all visualizations"""
        start_time = time.time()

        self.ax.clear()  # Clear the axis before re-drawing
        self.ax.grid(True)  # Re-enable grid

        self.ax.set_xlim(self.max_min_x)
        self.ax.set_ylim(self.max_min_y)

        for name, pos_data in self.positions.items():
            trail = pos_data["trail"]
            if not trail:
                continue

            # Extract coordinates
            x_coords = [p[0] for p in trail]
            y_coords = [p[1] for p in trail]

            # Calculate alpha values for fade effect
            alphas = np.linspace(0.2, 1, len(trail) - 1)  # One alpha per segment

            # Draw trail with fade effect
            for i in range(len(trail) - 1):
                color = (*pos_data["color"][:3], alphas[i])  # Alpha for current segment
                self.ax.plot(
                    [x_coords[i], x_coords[i + 1]],
                    [y_coords[i], y_coords[i + 1]],
                    color=color,
                    linewidth=1,
                )

            # Draw current position
            current_pos = trail[-1]
            self.ax.plot(
                current_pos[0],
                current_pos[1],
                "o",
                color=pos_data["color"],
                markersize=8,
                label=name,
            )

            # Draw direction indicator
            angle = np.deg2rad(current_pos[2])
            arrow_length = 0.5
            dx = arrow_length * np.cos(angle)
            dy = arrow_length * np.sin(angle)
            self.ax.arrow(
                current_pos[0],
                current_pos[1],
                dx,
                dy,
                head_width=0.1,
                head_length=0.2,
                color=pos_data["color"],
            )

        # Update legend
        self.ax.legend()

        # Refresh the plot
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

        # Measure frame time
        frame_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        self.frame_times.append(frame_time)
        if len(self.frame_times) > self.max_frame_times:
            self.frame_times.pop(0)

        # Print average frame time every 60 frames
        if len(self.frame_times) == self.max_frame_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            print(
                f"Average frame time: {avg_frame_time:.2f}ms ({1000 / avg_frame_time:.1f} FPS)"
            )

        return True

    def close(self):
        """Close the visualization window"""
        plt.close(self.fig)
