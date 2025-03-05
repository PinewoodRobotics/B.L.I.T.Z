import asyncio
import numpy as np
from rplidar import RPLidar


class LidarBridge:
    def __init__(self, lidar: RPLidar, name: str, transformation: np.ndarray):
        """
        transformation is a 4x4 numpy array
        """

        self.lidar = lidar
        self.last_scan: list[tuple[float, float, float]] = []
        self.name = name
        self.transformation = transformation

    async def run(self):
        while True:
            try:
                for scan in self.lidar.iter_scans():
                    self.last_scan = scan
            except Exception as e:
                print(e)
                await asyncio.sleep(0.1)

    def to_robot_centered(self, np_array: np.ndarray) -> np.ndarray:
        """
        Transform a point from lidar coordinates to robot-centered coordinates

        Args:
            np_array: A 1x2 numpy vector representing (x, y) coordinates

        Returns:
            Transformed coordinates as a numpy array
        """

        homogeneous = np.array([np_array[0], np_array[1], 0, 1])
        result = homogeneous @ self.transformation
        return result[:2]
