import numpy as np


class DefaultCamera:
    name = "default"
    camera_path = "0"
    width = 800
    height = 600
    max_fps = 30
    camera_matrix = np.eye(3)
    dist_coeff = np.zeros(5)
