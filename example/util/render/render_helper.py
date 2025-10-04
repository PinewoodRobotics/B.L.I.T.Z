import pyvista as pv
import asyncio
import numpy as np


class AsyncPyVistaVisualizer:
    def __init__(self):
        self.plotter = pv.Plotter(window_size=(800, 600))
        self.plotter.add_axes()
        self.plotter.show(interactive_update=True)
        self.spheres = []

    def update_spheres(self, tags):
        """Update the spheres dynamically based on the tag positions."""
        self.plotter.clear()  # Clear the plotter to refresh geometries
        for tag in tags:
            position = np.array(
                [
                    tag.position_x_relative,
                    tag.position_y_relative,
                    tag.position_z_relative,
                ]
            )
            sphere = pv.Sphere(radius=0.05, center=position)
            self.plotter.add_mesh(sphere, color="blue")
        self.plotter.render()

    async def run_visualization(self):
        while True:
            self.plotter.update()  # Update the plotter
            await asyncio.sleep(0.01)  # Adjust refresh rate
