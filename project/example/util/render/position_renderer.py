from matplotlib import pyplot as plt
import numpy as np


class PositionVisualizer:
    def __init__(self, window_size=(10, 8), trail_length=25):
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
        self.ax.set_xlim(-3, 3)
        self.ax.set_ylim(-3, 3)
        plt.show()

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

        self._draw_frame()
        return True

    def _draw_frame(self):
        """Update all visualizations"""
        self.ax.clear()  # Clear the axis before re-drawing
        self.ax.grid(True)  # Re-enable grid
        self.ax.set_xlim(-5, 5)
        self.ax.set_ylim(-5, 5)

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
        return True

    def close(self):
        """Close the visualization window"""
        plt.close(self.fig)
