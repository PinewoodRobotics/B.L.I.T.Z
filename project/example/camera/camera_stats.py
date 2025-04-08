import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import time
import os
import sys
import asyncio
from project.common.autobahn_python.autobahn import Autobahn
from project.common.autobahn_python.util import Address
from generated.status.CameraStatus_pb2 import CameraStatus


class CameraStatsVisualizer:
    def __init__(self):
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, 1, figsize=(10, 12))
        self.fig.suptitle("Camera Statistics")

        # Initialize data storage
        self.max_points = 100
        self.times = []
        self.frame_times = []
        self.inference_times = []
        self.fps_values = []
        self.avg_fps_values = []
        self.fps_window = 10  # Window size for moving average

        # Setup plots
        (self.line1,) = self.ax1.plot([], [], "b-", label="Frame Time")
        (self.line2,) = self.ax2.plot([], [], "r-", label="Inference Time")
        (self.line3,) = self.ax3.plot([], [], "g-", label="Avg FPS")

        # Configure axes
        self.ax1.set_title("Frame Time")
        self.ax1.set_ylabel("Time (ms)")
        self.ax1.grid(True)
        self.ax1.legend()

        self.ax2.set_title("Inference Time")
        self.ax2.set_ylabel("Time (ms)")
        self.ax2.grid(True)
        self.ax2.legend()

        self.ax3.set_title("Average FPS")
        self.ax3.set_ylabel("Frames per second")
        self.ax3.grid(True)
        self.ax3.legend()

        # Set initial limits
        self.ax1.set_ylim(0, 100)
        self.ax2.set_ylim(0, 100)
        self.ax3.set_ylim(0, 60)

    def update(self, frame):
        # Update plot data
        self.line1.set_data(self.times, self.frame_times)
        self.line2.set_data(self.times, self.inference_times)
        self.line3.set_data(self.times, self.avg_fps_values)

        # Update axis limits
        if self.times:
            self.ax1.set_xlim(self.times[0], self.times[-1])
            self.ax2.set_xlim(self.times[0], self.times[-1])
            self.ax3.set_xlim(self.times[0], self.times[-1])

            # Auto-scale y-axis based on data
            self.ax1.set_ylim(0, max(self.frame_times) * 1.2)
            self.ax2.set_ylim(0, max(self.inference_times) * 1.2)
            if self.avg_fps_values:
                self.ax3.set_ylim(0, max(self.avg_fps_values) * 1.2)

        return self.line1, self.line2, self.line3

    def add_data(self, frame_time, inference_time):
        current_time = time.time()
        self.times.append(current_time)
        self.frame_times.append(frame_time)  # Already in ms, don't convert
        self.inference_times.append(inference_time)  # Already in ms, don't convert

        # Calculate FPS (1000/frame_time since frame time is in ms)
        fps = 1000 / frame_time if frame_time > 0 else 0
        self.fps_values.append(fps)

        # Calculate moving average FPS
        window_start = max(0, len(self.fps_values) - self.fps_window)
        avg_fps = sum(self.fps_values[window_start:]) / (
            len(self.fps_values) - window_start
        )
        self.avg_fps_values.append(avg_fps)

        # Add debug prints
        print(
            f"Added data point - Frame time: {frame_time:.2f}ms, Inference time: {inference_time:.2f}ms, FPS: {fps:.2f}, Avg FPS: {avg_fps:.2f}"
        )

        # Keep only the last max_points
        if len(self.times) > self.max_points:
            self.times = self.times[-self.max_points :]
            self.frame_times = self.frame_times[-self.max_points :]
            self.inference_times = self.inference_times[-self.max_points :]
            self.fps_values = self.fps_values[-self.max_points :]
            self.avg_fps_values = self.avg_fps_values[-self.max_points :]

        # Update the plot data immediately
        self.update(None)
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()


async def main():
    plt.ion()  # Enable interactive mode

    visualizer = CameraStatsVisualizer()
    stop_event = asyncio.Event()

    # Create Autobahn connection
    autobahn_server = Autobahn(Address("10.47.65.12", 8080))
    await autobahn_server.begin()

    async def on_camera_status(message: bytes):
        # print(f"Received message: {message}")
        try:
            camera_status = CameraStatus()
            camera_status.ParseFromString(message)
            if camera_status.name == "front_right":
                visualizer.add_data(
                    camera_status.frame_time, camera_status.inference_time
                )
            # Remove plt.pause() as we're updating in add_data now
        except Exception as e:
            print(f"Error processing camera status: {e}", file=sys.stderr)

    # Subscribe to camera status topic
    await autobahn_server.subscribe("apriltag/stats", on_camera_status)

    try:
        await stop_event.wait()
    finally:
        plt.close()


if __name__ == "__main__":
    asyncio.run(main())
